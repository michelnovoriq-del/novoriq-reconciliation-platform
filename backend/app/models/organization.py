import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember", back_populates="organization", cascade="all, delete-orphan"
    )
    uploaded_files: Mapped[list["UploadedFile"]] = relationship(
        "UploadedFile", back_populates="organization"
    )
    reconciliation_runs: Mapped[list["ReconciliationRun"]] = relationship(
        "ReconciliationRun", back_populates="organization"
    )
    subscription: Mapped["OrganizationSubscription | None"] = relationship(
        "OrganizationSubscription", back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )
    usage_periods: Mapped[list["UsagePeriod"]] = relationship(
        "UsagePeriod", back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "organization_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), default="owner", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="organization_memberships")
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="members"
    )
