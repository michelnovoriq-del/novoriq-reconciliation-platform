"""add rejected records

Revision ID: 20260622_0003
Revises: 20260621_0002
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260622_0003"
down_revision: Union[str, None] = "20260621_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rejected_records",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=False),
        sa.Column("field_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["uploaded_file_id"], ["uploaded_files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rejected_records_organization_id"), "rejected_records", ["organization_id"])
    op.create_index(op.f("ix_rejected_records_uploaded_file_id"), "rejected_records", ["uploaded_file_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_rejected_records_uploaded_file_id"), table_name="rejected_records")
    op.drop_index(op.f("ix_rejected_records_organization_id"), table_name="rejected_records")
    op.drop_table("rejected_records")
