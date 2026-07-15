import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.dependencies import get_active_organization, get_current_user
from app.models import Organization, User
from app.schemas.file import (
    ColumnMapping,
    FilePreviewResponse,
    NormalizeFileResponse,
    UploadedFileResponse,
)
from app.schemas.rejected_record import RejectedRecordListResponse
from app.services.file_service import (
    list_uploaded_files,
    list_rejected_records,
    normalize_uploaded_file,
    preview_uploaded_file,
    save_uploaded_file,
    delete_uploaded_file,
)


router = APIRouter(prefix="/files", tags=["files"])


@router.get("", response_model=list[UploadedFileResponse])
def list_files(
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_active_organization),
):
    return list_uploaded_files(db, organization=organization)


@router.post("/upload", response_model=UploadedFileResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(...),
    prohibited_data_acknowledged: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_active_organization),
):
    settings = get_settings()
    if settings.is_production and settings.storage_backend == "local" and not settings.allow_ephemeral_test_uploads:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Uploads are unavailable until persistent private storage is configured.",
        )
    return save_uploaded_file(
        db,
        upload=file,
        user=current_user,
        organization=organization,
        prohibited_data_acknowledged=prohibited_data_acknowledged,
    )


@router.get("/{file_id}/preview", response_model=FilePreviewResponse)
def preview(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_active_organization),
) -> FilePreviewResponse:
    uploaded_file, columns, rows = preview_uploaded_file(
        db, file_id=file_id, user=current_user, organization=organization
    )
    return FilePreviewResponse(file_id=uploaded_file.id, columns=columns, sample_rows=rows)


@router.post("/{file_id}/normalize", response_model=NormalizeFileResponse)
def normalize(
    file_id: uuid.UUID,
    payload: ColumnMapping,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_active_organization),
) -> NormalizeFileResponse:
    return normalize_uploaded_file(
        db,
        file_id=file_id,
        mapping=payload,
        user=current_user,
        organization=organization,
    )


@router.get("/{file_id}/rejected-records", response_model=RejectedRecordListResponse)
def rejected_records(
    file_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_active_organization),
) -> RejectedRecordListResponse:
    return list_rejected_records(
        db, file_id=file_id, organization=organization, offset=offset, limit=limit
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_active_organization),
):
    delete_uploaded_file(db, file_id=file_id, user=current_user, organization=organization)
