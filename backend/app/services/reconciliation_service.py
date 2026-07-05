import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, ReconciliationRun, User
from app.services.audit_service import create_audit_log
from app.services.file_service import get_file_for_org


def create_reconciliation_run(
    db: Session,
    *,
    file_a_id: uuid.UUID,
    file_b_id: uuid.UUID,
    user: User,
    organization: Organization,
) -> ReconciliationRun:
    if file_a_id == file_b_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select two different uploaded files.",
        )
    get_file_for_org(db, file_a_id, organization.id)
    get_file_for_org(db, file_b_id, organization.id)
    run = ReconciliationRun(
        organization_id=organization.id,
        created_by_user_id=user.id,
        file_a_id=file_a_id,
        file_b_id=file_b_id,
        status="created",
    )
    db.add(run)
    db.flush()
    create_audit_log(
        db,
        organization_id=organization.id,
        user_id=user.id,
        action="reconciliation_run_created",
        entity_type="reconciliation_run",
        entity_id=run.id,
        metadata={"file_a_id": str(file_a_id), "file_b_id": str(file_b_id)},
    )
    db.commit()
    db.refresh(run)
    return run


def list_reconciliation_runs(db: Session, organization: Organization) -> list[ReconciliationRun]:
    return list(
        db.scalars(
            select(ReconciliationRun)
            .where(ReconciliationRun.organization_id == organization.id)
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
        )
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reconciliation run not found.",
        )
    return run
