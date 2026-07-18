import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MatchResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "match_results"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    reconciliation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reconciliation_runs.id"), nullable=False, index=True
    )
    file_a_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("normalized_records.id"), nullable=True
    )
    file_b_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("normalized_records.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    suggested_status: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_difference: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    date_difference_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_similarity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description_similarity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    duplicate_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reconciliation_run: Mapped["ReconciliationRun"] = relationship(
        "ReconciliationRun", back_populates="match_results"
    )
    file_a_record: Mapped["NormalizedRecord | None"] = relationship(
        "NormalizedRecord", foreign_keys=[file_a_record_id]
    )
    file_b_record: Mapped["NormalizedRecord | None"] = relationship(
        "NormalizedRecord", foreign_keys=[file_b_record_id]
    )
    reviewed_by_user: Mapped["User | None"] = relationship("User")
