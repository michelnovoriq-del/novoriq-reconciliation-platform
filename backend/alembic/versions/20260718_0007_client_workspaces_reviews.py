"""client workspaces and review metadata

Revision ID: 20260718_0007
Revises: 20260718_0006
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260718_0007"
down_revision: Union[str, None] = "20260718_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("client_workspaces",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False), sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True), sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]), sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("organization_id", "slug", name="uq_client_workspaces_org_slug"))
    op.create_index("ix_client_workspaces_organization_id", "client_workspaces", ["organization_id"])
    for table in ("uploaded_files", "reconciliation_runs", "audit_logs"):
        op.add_column(table, sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(f"fk_{table}_workspace_id", table, "client_workspaces", ["workspace_id"], ["id"])
        op.create_index(f"ix_{table}_workspace_id", table, ["workspace_id"])
    op.add_column("match_results", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column("match_results", sa.Column("suggested_status", sa.String(50), nullable=True))
    op.execute("UPDATE match_results SET suggested_status = status")
    op.alter_column("match_results", "suggested_status", nullable=False)
    op.add_column("match_results", sa.Column("duplicate_group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("match_results", sa.Column("duplicate_reason", sa.Text(), nullable=True))
    op.create_index("ix_match_results_duplicate_group_id", "match_results", ["duplicate_group_id"])

def downgrade() -> None:
    op.drop_index("ix_match_results_duplicate_group_id", table_name="match_results")
    for column in ("duplicate_reason", "duplicate_group_id", "suggested_status", "review_notes"): op.drop_column("match_results", column)
    for table in ("audit_logs", "reconciliation_runs", "uploaded_files"):
        op.drop_index(f"ix_{table}_workspace_id", table_name=table); op.drop_constraint(f"fk_{table}_workspace_id", table, type_="foreignkey"); op.drop_column(table, "workspace_id")
    op.drop_index("ix_client_workspaces_organization_id", table_name="client_workspaces"); op.drop_table("client_workspaces")
