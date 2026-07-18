import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_active_organization, get_current_user
from app.models import Organization, User
from app.schemas.match_result import MatchActionResponse
from pydantic import BaseModel, Field
from app.services.matching_service import mark_unmatched_reviewed, review_match, undo_review


router = APIRouter(prefix="/match-results", tags=["match-results"])

class ReviewNote(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


@router.post("/{match_id}/approve", response_model=MatchActionResponse)
def approve_match(match_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)):
    return review_match(db, match_id=match_id, decision="approved", user=current_user, organization=organization)


@router.post("/{match_id}/reject", response_model=MatchActionResponse)
def reject_match(match_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)):
    return review_match(db, match_id=match_id, decision="rejected", user=current_user, organization=organization)

@router.post("/{match_id}/mark-unmatched-reviewed", response_model=MatchActionResponse)
def mark_reviewed(match_id: uuid.UUID, payload: ReviewNote, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)):
    return mark_unmatched_reviewed(db, match_id=match_id, notes=payload.notes, user=current_user, organization=organization)

@router.post("/{match_id}/undo-review", response_model=MatchActionResponse)
def undo(match_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), organization: Organization = Depends(get_active_organization)):
    return undo_review(db, match_id=match_id, user=current_user, organization=organization)
