import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import MatchResult, Organization, ReconciliationRun, User
from app.services.audit_service import create_audit_log
from app.services.entitlement_service import can_create_reconciliation
from app.services.file_service import get_file_for_org
from app.services.usage_service import increment_reconciliation_usage
from app.models.base import utc_now


def create_reconciliation_run(
    db: Session,
    *,
    file_a_id: uuid.UUID,
    file_b_id: uuid.UUID,
    workspace_id: uuid.UUID | None = None,
    user: User,
    organization: Organization,
) -> ReconciliationRun:
    if file_a_id == file_b_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select two different uploaded files.",
        )
    can_create_reconciliation(db, organization.id)
    file_a = get_file_for_org(db, file_a_id, organization.id)
    file_b = get_file_for_org(db, file_b_id, organization.id)
    if workspace_id:
        from app.services.client_workspace_service import get_workspace
        get_workspace(db, workspace_id, organization)
        if file_a.workspace_id != workspace_id or file_b.workspace_id != workspace_id:
            raise HTTPException(status_code=400, detail="Both files must belong to the selected client workspace.")
    run = ReconciliationRun(
        organization_id=organization.id,
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        file_a_id=file_a_id,
        file_b_id=file_b_id,
        status="created",
    )
    db.add(run)
    db.flush()
    increment_reconciliation_usage(db, organization.id)
    create_audit_log(
        db,
        organization_id=organization.id,
        user_id=user.id,
        action="reconciliation_run_created",
        entity_type="reconciliation_run",
        entity_id=run.id,
        metadata={"file_a_id": str(file_a_id), "file_b_id": str(file_b_id)},
        workspace_id=workspace_id,
    )
    db.commit()
    db.refresh(run)
    return run


def list_reconciliation_runs(db: Session, organization: Organization) -> list[ReconciliationRun]:
    return list(
        db.scalars(
            select(ReconciliationRun)
            .where(ReconciliationRun.organization_id == organization.id, ReconciliationRun.deleted_at.is_(None))
            .order_by(ReconciliationRun.created_at.desc())
        )
    )


def get_reconciliation_run(
    db: Session, *, run_id: uuid.UUID, organization: Organization
) -> ReconciliationRun:
    run = db.scalar(
        select(ReconciliationRun).where(
            ReconciliationRun.id == run_id,
            ReconciliationRun.organization_id == organization.id,
            ReconciliationRun.deleted_at.is_(None),
        )
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reconciliation run not found.",
        )
    return run


def delete_reconciliation_run(
    db: Session, *, run_id: uuid.UUID, user: User, organization: Organization
) -> None:
    run = get_reconciliation_run(db, run_id=run_id, organization=organization)
    db.execute(
        delete(MatchResult).where(
            MatchResult.reconciliation_run_id == run.id,
            MatchResult.organization_id == organization.id,
        )
    )
    run.status = "deleted"
    run.deleted_at = utc_now()
    run.data_purged_at = utc_now()
    create_audit_log(
        db,
        organization_id=organization.id,
        user_id=user.id,
        action="reconciliation_run_deleted",
        entity_type="reconciliation_run",
        entity_id=run.id,
    )
    db.commit()
