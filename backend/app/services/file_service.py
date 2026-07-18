import logging
import uuid
from datetime import timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import MatchResult, NormalizedRecord, Organization, ReconciliationRun, RejectedRecord, UploadedFile, User
from app.models.base import utc_now
from app.schemas.file import ColumnMapping
from app.schemas.rejected_record import RejectedRecordListResponse
from app.services.audit_service import create_audit_log
from app.services.entitlement_service import can_process_rows, can_upload_file
from app.services.normalizer_service import RowNormalizationError, normalize_row
from app.services.parser_service import count_rows, preview_file, read_file
from app.services.storage import get_storage_backend
from app.services.upload_safety import detect_prohibited_sensitive_data, validate_upload_metadata
from app.services.usage_service import increment_upload_usage


logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def _file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".xlsx":
        return "excel"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type. Upload CSV first; Excel support is prepared.",
    )


def get_file_for_org(db: Session, file_id: uuid.UUID, organization_id: uuid.UUID) -> UploadedFile:
    uploaded_file = db.scalar(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.organization_id == organization_id,
            UploadedFile.deleted_at.is_(None),
        )
    )
    if not uploaded_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return uploaded_file


def list_uploaded_files(db: Session, organization: Organization) -> list[UploadedFile]:
    return list(
        db.scalars(
            select(UploadedFile)
            .where(UploadedFile.organization_id == organization.id, UploadedFile.deleted_at.is_(None))
            .order_by(UploadedFile.created_at.desc())
        )
    )


def save_uploaded_file(
    db: Session,
    *,
    upload: UploadFile,
    user: User,
    organization: Organization,
    prohibited_data_acknowledged: bool,
    workspace_id: uuid.UUID | None = None,
) -> UploadedFile:
    if not prohibited_data_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "PROHIBITED_DATA_ACKNOWLEDGEMENT_REQUIRED",
                "message": "Confirm that the upload excludes prohibited payment-card, credential, and secret data.",
            },
        )
    can_upload_file(db, organization.id)
    if workspace_id:
        from app.services.client_workspace_service import get_workspace
        workspace = get_workspace(db, workspace_id, organization)
        if workspace.status != "active":
            raise HTTPException(status_code=400, detail="Choose an active client workspace.")
    settings = get_settings()
    original_filename = upload.filename or "upload.csv"
    validate_upload_metadata(original_filename, upload.content_type)
    file_type = _file_type(original_filename)
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / "tmp" / f"{uuid.uuid4()}{Path(original_filename).suffix.lower()}"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    max_size_bytes = settings.max_upload_size_mb_free * 1024 * 1024
    bytes_written = 0
    with temp_path.open("wb") as output:
        while chunk := upload.file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > max_size_bytes:
                output.close()
                temp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded file exceeds the plan size limit.")
            output.write(chunk)
    if detect_prohibited_sensitive_data(temp_path):
        temp_path.unlink(missing_ok=True)
        create_audit_log(
            db,
            organization_id=organization.id,
            user_id=user.id,
            action="prohibited_upload_rejected",
            entity_type="uploaded_file",
            metadata={"original_filename": original_filename},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "PROHIBITED_SENSITIVE_DATA_DETECTED",
                "message": "This upload may contain prohibited payment-card or authentication data. Remove those fields and upload a redacted export.",
            },
        )

    file_id = uuid.uuid4()
    stored_filename = f"{file_id}{Path(original_filename).suffix.lower()}"
    object_key = f"organizations/{organization.id}/uploads/{file_id}/{uuid.uuid4()}{Path(original_filename).suffix.lower()}"
    file_path = get_storage_backend().save_file(temp_path, object_key)

    uploaded_file = UploadedFile(
        id=file_id,
        organization_id=organization.id,
        workspace_id=workspace_id,
        uploaded_by_user_id=user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        file_type=file_type,
        status="uploaded",
        retention_expires_at=utc_now() + timedelta(hours=24),
    )
    db.add(uploaded_file)
    db.flush()
    create_audit_log(
        db,
        organization_id=organization.id,
        user_id=user.id,
        action="file_uploaded",
        entity_type="uploaded_file",
        entity_id=uploaded_file.id,
        metadata={"original_filename": original_filename},
        workspace_id=workspace_id,
    )
    db.commit()
    db.refresh(uploaded_file)
    return uploaded_file


def preview_uploaded_file(
    db: Session, *, file_id: uuid.UUID, user: User, organization: Organization
) -> tuple[UploadedFile, list[str], list[dict]]:
    uploaded_file = get_file_for_org(db, file_id, organization.id)
    try:
        columns, rows = preview_file(uploaded_file.file_path)
        row_count = count_rows(uploaded_file.file_path)
        can_process_rows(db, organization.id, row_count)
        uploaded_file.row_count = row_count
        uploaded_file.status = "previewed"
        create_audit_log(
            db,
            organization_id=organization.id,
            user_id=user.id,
            action="file_previewed",
            entity_type="uploaded_file",
            entity_id=uploaded_file.id,
            workspace_id=uploaded_file.workspace_id,
        )
        db.commit()
        db.refresh(uploaded_file)
        return uploaded_file, columns, rows
    except Exception as exc:
        uploaded_file.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail=f"Could not preview file: {exc}") from exc


def normalize_uploaded_file(
    db: Session, *, file_id: uuid.UUID, mapping: ColumnMapping, user: User, organization: Organization
) -> dict:
    uploaded_file = get_file_for_org(db, file_id, organization.id)

    try:
        columns, rows = read_file(uploaded_file.file_path)
    except (OSError, ValueError, UnicodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse uploaded file: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected parser error for uploaded file %s", file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while normalizing file. Check server logs.",
        ) from exc

    validate_column_mapping(mapping, columns)
    can_process_rows(db, organization.id, len(rows))

    valid_records: list[NormalizedRecord] = []
    rejected_records: list[RejectedRecord] = []
    for index, row in enumerate(rows, start=1):
        raw_data = {str(key): _json_value(value) for key, value in row.items()}
        try:
            normalized = normalize_row(raw_data, mapping)
            valid_records.append(
                NormalizedRecord(
                    organization_id=organization.id,
                    uploaded_file_id=uploaded_file.id,
                    source_row_number=index,
                    **normalized,
                )
            )
        except RowNormalizationError as exc:
            rejected_records.append(
                RejectedRecord(
                    organization_id=organization.id,
                    uploaded_file_id=uploaded_file.id,
                    source_row_number=index,
                    raw_data=raw_data,
                    rejection_reason=exc.reason,
                    field_errors=exc.field_errors,
                )
            )
        except Exception:
            logger.exception("Unexpected error normalizing file %s row %s", file_id, index)
            rejected_records.append(
                RejectedRecord(
                    organization_id=organization.id,
                    uploaded_file_id=uploaded_file.id,
                    source_row_number=index,
                    raw_data=raw_data,
                    rejection_reason="unexpected_row_error",
                    field_errors={"row": "An unexpected error occurred while processing this row."},
                )
            )

    valid_count = len(valid_records)
    rejected_count = len(rejected_records)
    file_status = (
        "normalized"
        if valid_count and not rejected_count
        else "normalized_with_rejections"
        if valid_count
        else "failed_normalization"
    )
    action = (
        "file_normalized"
        if file_status == "normalized"
        else "file_normalized_with_rejections"
        if file_status == "normalized_with_rejections"
        else "file_normalization_failed"
    )

    try:
        affected_runs = list(
            db.scalars(
                select(ReconciliationRun).where(
                    ReconciliationRun.organization_id == organization.id,
                    ReconciliationRun.deleted_at.is_(None),
                    or_(
                        ReconciliationRun.file_a_id == file_id,
                        ReconciliationRun.file_b_id == file_id,
                    ),
                )
            )
        )
        if affected_runs:
            db.execute(
                delete(MatchResult).where(
                    MatchResult.organization_id == organization.id,
                    MatchResult.reconciliation_run_id.in_([run.id for run in affected_runs]),
                )
            )
            for run in affected_runs:
                # Results reference the previous normalized-record version. Resetting
                # lets the existing run be executed again against the latest mapping.
                run.status = "created"
        db.execute(
            delete(NormalizedRecord).where(
                NormalizedRecord.uploaded_file_id == file_id,
                NormalizedRecord.organization_id == organization.id,
            )
        )
        db.execute(
            delete(RejectedRecord).where(
                RejectedRecord.uploaded_file_id == file_id,
                RejectedRecord.organization_id == organization.id,
            )
        )
        db.add_all(valid_records)
        db.add_all(rejected_records)
        uploaded_file.row_count = len(rows)
        uploaded_file.status = file_status
        uploaded_file.normalization_mapping = mapping.model_dump(exclude_none=True)
        uploaded_file.retention_expires_at = utc_now() + timedelta(hours=24)
        increment_upload_usage(db, organization.id, rows_processed=len(rows))
        create_audit_log(
            db,
            organization_id=organization.id,
            user_id=user.id,
            action=action,
            entity_type="uploaded_file",
            entity_id=uploaded_file.id,
            workspace_id=uploaded_file.workspace_id,
            metadata={
                "uploaded_file_id": str(uploaded_file.id),
                "total_rows": len(rows),
                "valid_rows": valid_count,
                "rejected_rows": rejected_count,
                "mapping": mapping.model_dump(),
                "invalidated_reconciliation_runs": len(affected_runs),
            },
        )
        db.flush()
        db.commit()
        for record in rejected_records[:5]:
            db.refresh(record)
    except Exception as exc:
        db.rollback()
        logger.exception("Database error while normalizing uploaded file %s", file_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error while normalizing file. Check server logs.",
        ) from exc

    result = {
        "uploaded_file_id": uploaded_file.id,
        "status": "failed" if not valid_count else file_status,
        "total_rows": len(rows),
        "valid_rows": valid_count,
        "rejected_rows": rejected_count,
        "rejected_examples": rejected_records[:5],
        "message": (
            f"Normalized {valid_count} rows. Rejected {rejected_count} rows with validation errors."
            if rejected_count
            else f"Normalized {valid_count} rows."
        ),
    }
    if not valid_count:
        # Rejections are committed so users can inspect and fix the source data.
        from app.schemas.file import NormalizeFileResponse

        detail = NormalizeFileResponse.model_validate(result).model_dump(mode="json")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return result


def validate_column_mapping(mapping: ColumnMapping, columns: list[str]) -> None:
    required_fields = ("date", "amount", "reference")
    missing_required_fields = [field for field in required_fields if not getattr(mapping, field)]
    invalid_mapped_columns = {
        field: f"{column} column was not found in file"
        for field in ColumnMapping.model_fields
        if (column := getattr(mapping, field)) and column not in columns
    }
    if missing_required_fields or invalid_mapped_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid column mapping.",
                "missing_required_fields": missing_required_fields,
                "invalid_mapped_columns": invalid_mapped_columns,
                "available_columns": columns,
            },
        )


def _json_value(value: object) -> object:
    if value is None:
        return None
    try:
        # pandas uses NaN/NaT sentinels that PostgreSQL JSONB cannot encode safely.
        import pandas as pd

        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def list_rejected_records(
    db: Session,
    *,
    file_id: uuid.UUID,
    organization: Organization,
    offset: int = 0,
    limit: int = 100,
) -> RejectedRecordListResponse:
    uploaded_file = db.scalar(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.organization_id == organization.id,
            UploadedFile.deleted_at.is_(None),
        )
    )
    if not uploaded_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    filters = (
        RejectedRecord.uploaded_file_id == uploaded_file.id,
        RejectedRecord.organization_id == organization.id,
    )
    total = db.scalar(select(func.count()).select_from(RejectedRecord).where(*filters)) or 0
    records = list(
        db.scalars(
            select(RejectedRecord)
            .where(*filters)
            .order_by(RejectedRecord.source_row_number)
            .offset(offset)
            .limit(limit)
        )
    )
    return RejectedRecordListResponse(
        uploaded_file_id=uploaded_file.id, total_rejected=total, records=records
    )


def delete_uploaded_file(
    db: Session, *, file_id: uuid.UUID, user: User, organization: Organization
) -> None:
    uploaded_file = get_file_for_org(db, file_id, organization.id)
    active_run_count = db.scalar(
        select(func.count()).select_from(ReconciliationRun).where(
            or_(
                ReconciliationRun.file_a_id == file_id,
                ReconciliationRun.file_b_id == file_id,
            ),
            ReconciliationRun.organization_id == organization.id,
            ReconciliationRun.deleted_at.is_(None),
        )
    ) or 0
    if active_run_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delete dependent reconciliation runs before deleting this file.",
        )
    try:
        path = Path(uploaded_file.file_path)
        if path.is_absolute():
            path.unlink(missing_ok=True)
        else:
            get_storage_backend().delete_file(uploaded_file.file_path)
    except Exception:
        logger.exception("Could not delete stored file %s", uploaded_file.id)
        raise HTTPException(status_code=500, detail="Could not delete stored file.") from None
    db.execute(delete(NormalizedRecord).where(NormalizedRecord.uploaded_file_id == file_id, NormalizedRecord.organization_id == organization.id))
    db.execute(delete(RejectedRecord).where(RejectedRecord.uploaded_file_id == file_id, RejectedRecord.organization_id == organization.id))
    uploaded_file.status = "deleted"
    uploaded_file.deleted_at = utc_now()
    uploaded_file.storage_deleted_at = utc_now()
    create_audit_log(
        db,
        organization_id=organization.id,
        user_id=user.id,
        action="file_deleted",
        entity_type="uploaded_file",
        entity_id=uploaded_file.id,
    )
    db.commit()
