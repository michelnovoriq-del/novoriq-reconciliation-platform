import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_price_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    monthly_run_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    max_files_per_run: Mapped[int] = mapped_column(Integer, nullable=False)
    max_rows_per_file: Mapped[int] = mapped_column(Integer, nullable=False)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False)
    max_client_workspaces: Mapped[int] = mapped_column(Integer, nullable=False)
    detailed_retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    subscriptions: Mapped[list["OrganizationSubscription"]] = relationship(
        "OrganizationSubscription", back_populates="plan"
    )


class OrganizationSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_subscriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    billing_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    external_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="subscription")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscriptions")


class UsagePeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usage_periods"
    __table_args__ = (
        UniqueConstraint("organization_id", "period_start", "period_end", name="uq_usage_period_org_period"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reconciliation_runs_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_uploaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exports_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="usage_periods")


class WhopMembershipLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "whop_membership_links"
    __table_args__ = (
        UniqueConstraint("whop_membership_id", name="uq_whop_membership_links_membership_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    novoriq_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    whop_company_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whop_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    whop_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whop_member_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whop_membership_id: Mapped[str] = mapped_column(String(255), nullable=False)
    whop_plan_id: Mapped[str] = mapped_column(String(255), nullable=False)
    whop_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whop_manage_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    membership_status: Mapped[str] = mapped_column(String(100), nullable=False)
    mapped_plan_code: Mapped[str] = mapped_column(String(50), nullable=False)
    whop_email_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PendingWhopMembershipLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pending_whop_membership_links"
    __table_args__ = (
        UniqueConstraint("whop_membership_id", name="uq_pending_whop_membership_links_membership_id"),
    )

    whop_membership_id: Mapped[str] = mapped_column(String(255), nullable=False)
    whop_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    whop_email_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    whop_plan_id: Mapped[str] = mapped_column(String(255), nullable=False)
    whop_product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    membership_status: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(255), nullable=True)


class WhopWebhookEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "whop_webhook_events"
    __table_args__ = (
        UniqueConstraint("whop_event_id", name="uq_whop_webhook_events_event_id"),
    )

    whop_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_type: Mapped[str] = mapped_column(String(255), nullable=False)
    whop_company_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whop_membership_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), default="received", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
