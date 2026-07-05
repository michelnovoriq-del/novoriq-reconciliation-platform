"""add match results

Revision ID: 20260621_0002
Revises: 20260620_0001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260621_0002"
down_revision: Union[str, None] = "20260620_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_results",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reconciliation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_a_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_b_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("amount_difference", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("date_difference_days", sa.Integer(), nullable=True),
        sa.Column("reference_similarity", sa.Integer(), nullable=True),
        sa.Column("description_similarity", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["reconciliation_run_id"], ["reconciliation_runs.id"]),
        sa.ForeignKeyConstraint(["file_a_record_id"], ["normalized_records.id"]),
        sa.ForeignKeyConstraint(["file_b_record_id"], ["normalized_records.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_match_results_organization_id"), "match_results", ["organization_id"])
    op.create_index(op.f("ix_match_results_reconciliation_run_id"), "match_results", ["reconciliation_run_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_match_results_reconciliation_run_id"), table_name="match_results")
    op.drop_index(op.f("ix_match_results_organization_id"), table_name="match_results")
    op.drop_table("match_results")
