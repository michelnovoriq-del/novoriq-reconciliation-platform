"""plans usage retention

Revision ID: 20260709_0004
Revises: 20260622_0003
Create Date: 2026-07-09 00:04:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260709_0004"
down_revision: Union[str, None] = "20260622_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("monthly_price_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("monthly_run_limit", sa.Integer(), nullable=False),
        sa.Column("max_files_per_run", sa.Integer(), nullable=False),
        sa.Column("max_rows_per_file", sa.Integer(), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.Column("max_client_workspaces", sa.Integer(), nullable=False),
        sa.Column("detailed_retention_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plans_code"), "plans", ["code"], unique=True)

    op.create_table(
        "organization_subscriptions",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("billing_provider", sa.String(length=50), nullable=True),
        sa.Column("external_customer_id", sa.String(length=255), nullable=True),
        sa.Column("external_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index(op.f("ix_organization_subscriptions_organization_id"), "organization_subscriptions", ["organization_id"], unique=True)
    op.create_index(op.f("ix_organization_subscriptions_plan_id"), "organization_subscriptions", ["plan_id"], unique=False)

    op.create_table(
        "usage_periods",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconciliation_runs_used", sa.Integer(), nullable=False),
        sa.Column("files_uploaded", sa.Integer(), nullable=False),
        sa.Column("rows_processed", sa.Integer(), nullable=False),
        sa.Column("exports_generated", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "period_start", "period_end", name="uq_usage_period_org_period"),
    )
    op.create_index(op.f("ix_usage_periods_organization_id"), "usage_periods", ["organization_id"], unique=False)

    op.add_column("uploaded_files", sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("uploaded_files", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("uploaded_files", sa.Column("storage_deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reconciliation_runs", sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reconciliation_runs", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reconciliation_runs", sa.Column("data_purged_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("reconciliation_runs", "data_purged_at")
    op.drop_column("reconciliation_runs", "deleted_at")
    op.drop_column("reconciliation_runs", "retention_expires_at")
    op.drop_column("uploaded_files", "storage_deleted_at")
    op.drop_column("uploaded_files", "deleted_at")
    op.drop_column("uploaded_files", "retention_expires_at")
    op.drop_index(op.f("ix_usage_periods_organization_id"), table_name="usage_periods")
    op.drop_table("usage_periods")
    op.drop_index(op.f("ix_organization_subscriptions_plan_id"), table_name="organization_subscriptions")
    op.drop_index(op.f("ix_organization_subscriptions_organization_id"), table_name="organization_subscriptions")
    op.drop_table("organization_subscriptions")
    op.drop_index(op.f("ix_plans_code"), table_name="plans")
    op.drop_table("plans")
