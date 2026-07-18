import uuid
from datetime import datetime

from pydantic import BaseModel


class ReconciliationRunCreate(BaseModel):
    file_a_id: uuid.UUID
    file_b_id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    role_override_confirmed: bool = False
    role_override_reason: str | None = None


class ReconciliationRunResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    file_a_role: str = "unknown"
    file_b_role: str = "unknown"
    role_override_confirmed: bool = False
    created_by_user_id: uuid.UUID
    file_a_id: uuid.UUID
    file_b_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
