import uuid
from datetime import datetime

from pydantic import BaseModel


class RejectedRecordResponse(BaseModel):
    id: uuid.UUID
    uploaded_file_id: uuid.UUID
    source_row_number: int
    raw_data: dict
    rejection_reason: str
    field_errors: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RejectedRecordListResponse(BaseModel):
    uploaded_file_id: uuid.UUID
    total_rejected: int
    records: list[RejectedRecordResponse]
