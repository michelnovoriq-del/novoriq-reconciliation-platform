import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.rejected_record import RejectedRecordResponse


class UploadedFileResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    uploaded_by_user_id: uuid.UUID
    original_filename: str
    stored_filename: str
    file_type: str
    row_count: int | None = None
    status: str
    normalization_mapping: dict | None = None
    file_role: str = "unknown"
    detected_file_role: str = "unknown"
    file_role_confidence: float = 0
    file_role_signals: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FilePreviewResponse(BaseModel):
    file_id: uuid.UUID
    columns: list[str]
    sample_rows: list[dict]


class ColumnMapping(BaseModel):
    date: str | None = None
    amount: str | None = None
    reference: str | None = None
    description: str | None = None
    customer_name: str | None = None
    currency: str | None = None


class NormalizeFileResponse(BaseModel):
    uploaded_file_id: uuid.UUID
    status: str
    total_rows: int
    valid_rows: int
    rejected_rows: int
    rejected_examples: list[RejectedRecordResponse]
    message: str

class FileRoleUpdate(BaseModel):
    file_role: str
