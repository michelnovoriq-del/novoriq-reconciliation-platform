"""whop entitlements

Revision ID: 20260710_0005
Revises: 20260709_0004
Create Date: 2026-07-10 00:05:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260710_0005"
down_revision: Union[str, None] = "20260709_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET email_verified_at = COALESCE(email_verified_at, now())")
    op.create_index("ix_users_email_lower_unique", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "whop_membership_links",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("novoriq_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("whop_company_id", sa.String(length=255), nullable=True),
        sa.Column("whop_user_id", sa.String(length=255), nullable=False),
        sa.Column("whop_username", sa.String(length=255), nullable=True),
        sa.Column("whop_member_id", sa.String(length=255), nullable=True),
        sa.Column("whop_membership_id", sa.String(length=255), nullable=False),
        sa.Column("whop_plan_id", sa.String(length=255), nullable=False),
        sa.Column("whop_product_id", sa.String(length=255), nullable=True),
        sa.Column("whop_manage_url", sa.String(length=1024), nullable=True),
        sa.Column("membership_status", sa.String(length=100), nullable=False),
        sa.Column("mapped_plan_code", sa.String(length=50), nullable=False),
        sa.Column("whop_email_normalized", sa.String(length=255), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["novoriq_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("whop_membership_id", name="uq_whop_membership_links_membership_id"),
    )
    op.create_index(op.f("ix_whop_membership_links_novoriq_user_id"), "whop_membership_links", ["novoriq_user_id"], unique=False)
    op.create_index(op.f("ix_whop_membership_links_organization_id"), "whop_membership_links", ["organization_id"], unique=False)
    op.create_index(op.f("ix_whop_membership_links_whop_email_normalized"), "whop_membership_links", ["whop_email_normalized"], unique=False)
    op.create_index(op.f("ix_whop_membership_links_whop_user_id"), "whop_membership_links", ["whop_user_id"], unique=False)

    op.create_table(
        "pending_whop_membership_links",
        sa.Column("whop_membership_id", sa.String(length=255), nullable=False),
        sa.Column("whop_user_id", sa.String(length=255), nullable=False),
        sa.Column("whop_email_normalized", sa.String(length=255), nullable=False),
        sa.Column("whop_plan_id", sa.String(length=255), nullable=False),
        sa.Column("whop_product_id", sa.String(length=255), nullable=True),
        sa.Column("membership_status", sa.String(length=100), nullable=False),
        sa.Column("raw_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("whop_membership_id", name="uq_pending_whop_membership_links_membership_id"),
    )
    op.create_index(op.f("ix_pending_whop_membership_links_whop_email_normalized"), "pending_whop_membership_links", ["whop_email_normalized"], unique=False)
    op.create_index(op.f("ix_pending_whop_membership_links_whop_user_id"), "pending_whop_membership_links", ["whop_user_id"], unique=False)

    op.create_table(
        "whop_webhook_events",
        sa.Column("whop_event_id", sa.String(length=255), nullable=False),
        sa.Column("webhook_type", sa.String(length=255), nullable=False),
        sa.Column("whop_company_id", sa.String(length=255), nullable=True),
        sa.Column("whop_membership_id", sa.String(length=255), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=50), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("whop_event_id", name="uq_whop_webhook_events_event_id"),
    )
    op.create_index(op.f("ix_whop_webhook_events_whop_membership_id"), "whop_webhook_events", ["whop_membership_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_whop_webhook_events_whop_membership_id"), table_name="whop_webhook_events")
    op.drop_table("whop_webhook_events")
    op.drop_index(op.f("ix_pending_whop_membership_links_whop_user_id"), table_name="pending_whop_membership_links")
    op.drop_index(op.f("ix_pending_whop_membership_links_whop_email_normalized"), table_name="pending_whop_membership_links")
    op.drop_table("pending_whop_membership_links")
    op.drop_index(op.f("ix_whop_membership_links_whop_user_id"), table_name="whop_membership_links")
    op.drop_index(op.f("ix_whop_membership_links_whop_email_normalized"), table_name="whop_membership_links")
    op.drop_index(op.f("ix_whop_membership_links_organization_id"), table_name="whop_membership_links")
    op.drop_index(op.f("ix_whop_membership_links_novoriq_user_id"), table_name="whop_membership_links")
    op.drop_table("whop_membership_links")
    op.drop_index("ix_users_email_lower_unique", table_name="users")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified_at")
