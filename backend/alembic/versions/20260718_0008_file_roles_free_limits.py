"""file roles and free beta limits

Revision ID: 20260718_0008
Revises: 20260718_0007
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision: str="20260718_0008"; down_revision: Union[str,None]="20260718_0007"; branch_labels: Union[str,Sequence[str],None]=None; depends_on: Union[str,Sequence[str],None]=None
def upgrade():
    op.add_column("uploaded_files",sa.Column("file_role",sa.String(50),nullable=False,server_default="unknown"));op.add_column("uploaded_files",sa.Column("detected_file_role",sa.String(50),nullable=False,server_default="unknown"));op.add_column("uploaded_files",sa.Column("file_role_confidence",sa.Float(),nullable=False,server_default="0"));op.add_column("uploaded_files",sa.Column("file_role_signals",postgresql.JSONB(),nullable=False,server_default="[]"))
    op.add_column("reconciliation_runs",sa.Column("file_a_role",sa.String(50),nullable=False,server_default="unknown"));op.add_column("reconciliation_runs",sa.Column("file_b_role",sa.String(50),nullable=False,server_default="unknown"));op.add_column("reconciliation_runs",sa.Column("role_override_confirmed",sa.Boolean(),nullable=False,server_default=sa.false()));op.add_column("reconciliation_runs",sa.Column("role_override_reason",sa.Text(),nullable=True))
    op.execute("UPDATE plans SET monthly_run_limit=10, max_rows_per_file=1000 WHERE code='free'")
def downgrade():
    op.execute("UPDATE plans SET monthly_run_limit=2, max_rows_per_file=2500 WHERE code='free'")
    for c in ("role_override_reason","role_override_confirmed","file_b_role","file_a_role"):op.drop_column("reconciliation_runs",c)
    for c in ("file_role_signals","file_role_confidence","detected_file_role","file_role"):op.drop_column("uploaded_files",c)
