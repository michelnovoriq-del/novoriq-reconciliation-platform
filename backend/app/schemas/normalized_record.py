import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class NormalizedRecordResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    uploaded_file_id: uuid.UUID
    source_row_number: int
    transaction_date: date | None = None
    amount: Decimal | None = None
    reference: str | None = None
    description: str | None = None
    customer_name: str | None = None
    currency: str | None = None
    raw_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}
