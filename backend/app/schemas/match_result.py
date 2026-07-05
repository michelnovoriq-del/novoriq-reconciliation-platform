import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.normalized_record import NormalizedRecordResponse


class MatchResultResponse(BaseModel):
    id: uuid.UUID
    reconciliation_run_id: uuid.UUID
    file_a_record_id: uuid.UUID | None
    file_b_record_id: uuid.UUID | None
    status: str
    confidence_score: int
    match_reason: str | None
    amount_difference: Decimal | None
    date_difference_days: int | None
    reference_similarity: int | None
    description_similarity: int | None
    created_at: datetime
    reviewed_at: datetime | None
    file_a_record: NormalizedRecordResponse | None = None
    file_b_record: NormalizedRecordResponse | None = None

    model_config = {"from_attributes": True}


class ReconciliationSummary(BaseModel):
    total_matches: int
    green_count: int
    yellow_count: int
    red_count: int
    approved_count: int
    rejected_count: int


class ReconciliationResultsResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    green_matches: list[MatchResultResponse]
    yellow_possible_matches: list[MatchResultResponse]
    red_unmatched: list[MatchResultResponse]
    summary: ReconciliationSummary


class MatchActionResponse(BaseModel):
    id: uuid.UUID
    status: str
    reviewed_at: datetime

    model_config = {"from_attributes": True}
