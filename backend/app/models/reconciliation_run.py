import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReconciliationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reconciliation_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    file_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False
    )
    file_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="created", nullable=False)
    retention_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="reconciliation_runs"
    )
    created_by_user: Mapped["User"] = relationship(
        "User", back_populates="reconciliation_runs"
    )
    file_a: Mapped["UploadedFile"] = relationship("UploadedFile", foreign_keys=[file_a_id])
    file_b: Mapped["UploadedFile"] = relationship("UploadedFile", foreign_keys=[file_b_id])
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult", back_populates="reconciliation_run", cascade="all, delete-orphan"
    )
