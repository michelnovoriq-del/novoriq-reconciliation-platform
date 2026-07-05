import logging
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import NormalizedRecord, Organization, RejectedRecord, UploadedFile, User
from app.schemas.file import ColumnMapping
from app.schemas.rejected_record import RejectedRecordListResponse
from app.services.audit_service import create_audit_log
from app.services.normalizer_service import RowNormalizationError, normalize_row
from app.services.parser_service import count_rows, preview_file, read_file


logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def _file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".xlsx", ".xls"}:
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
        )
    )
    if not uploaded_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return uploaded_file


def list_uploaded_files(db: Session, organization: Organization) -> list[UploadedFile]:
    return list(
        db.scalars(
            select(UploadedFile)
            .where(UploadedFile.organization_id == organization.id)
            .order_by(UploadedFile.created_at.desc())
        )
    )


def save_uploaded_file(
    db: Session, *, upload: UploadFile, user: User, organization: Organization
) -> UploadedFile:
    settings = get_settings()
    original_filename = upload.filename or "upload.csv"
    file_type = _file_type(original_filename)
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4()}{Path(original_filename).suffix.lower()}"
    file_path = upload_dir / stored_filename

    with file_path.open("wb") as output:
        shutil.copyfileobj(upload.file, output)

    uploaded_file = UploadedFile(
        organization_id=organization.id,
        uploaded_by_user_id=user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        file_type=file_type,
        status="uploaded",
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
        uploaded_file.row_count = count_rows(uploaded_file.file_path)
        uploaded_file.status = "previewed"
        create_audit_log(
            db,
            organization_id=organization.id,
            user_id=user.id,
            action="file_previewed",
            entity_type="uploaded_file",
            entity_id=uploaded_file.id,
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
        db.execute(delete(NormalizedRecord).where(NormalizedRecord.uploaded_file_id == file_id))
        db.execute(delete(RejectedRecord).where(RejectedRecord.uploaded_file_id == file_id))
        db.add_all(valid_records)
        db.add_all(rejected_records)
        uploaded_file.row_count = len(rows)
        uploaded_file.status = file_status
        create_audit_log(
            db,
            organization_id=organization.id,
            user_id=user.id,
            action=action,
            entity_type="uploaded_file",
            entity_id=uploaded_file.id,
            metadata={
                "uploaded_file_id": str(uploaded_file.id),
                "total_rows": len(rows),
                "valid_rows": valid_count,
                "rejected_rows": rejected_count,
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
    uploaded_file = db.scalar(select(UploadedFile).where(UploadedFile.id == file_id))
    if not uploaded_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    if uploaded_file.organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this file.",
        )
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
