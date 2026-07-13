import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import OrganizationMember, Plan
from app.services.audit_service import create_audit_log
from app.services.plan_service import get_current_plan
from app.services.usage_service import get_current_usage


def _limit_error(*, plan: Plan, resource: str, limit: int, used: int, message: str, reset_at=None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "PLAN_LIMIT_REACHED",
            "message": message,
            "resource": resource,
            "limit": limit,
            "used": used,
            "remaining": max(limit - used, 0),
            "plan_code": plan.code,
            "reset_at": reset_at.isoformat() if reset_at else None,
        },
    )


def can_create_reconciliation(db: Session, organization_id: uuid.UUID) -> bool:
    plan = get_current_plan(db, organization_id)
    usage = get_current_usage(db, organization_id, lock=True)
    if usage.reconciliation_runs_used >= plan.monthly_run_limit:
        create_audit_log(
            db,
            organization_id=organization_id,
            user_id=None,
            action="plan_limit_reached",
            entity_type="usage_period",
            entity_id=usage.id,
            metadata={"resource": "reconciliation_runs", "plan_code": plan.code},
        )
        raise _limit_error(
            plan=plan,
            resource="reconciliation_runs",
            limit=plan.monthly_run_limit,
            used=usage.reconciliation_runs_used,
            message=f"You have used all reconciliation runs included in your {plan.name} plan.",
            reset_at=usage.period_end,
        )
    return True


def can_upload_file(db: Session, organization_id: uuid.UUID) -> bool:
    get_current_plan(db, organization_id)
    get_current_usage(db, organization_id, lock=True)
    return True


def can_process_rows(db: Session, organization_id: uuid.UUID, row_count: int) -> bool:
    plan = get_current_plan(db, organization_id)
    if row_count > plan.max_rows_per_file:
        raise _limit_error(
            plan=plan,
            resource="rows_per_file",
            limit=plan.max_rows_per_file,
            used=row_count,
            message=f"This file has {row_count} rows, above the {plan.name} limit of {plan.max_rows_per_file} rows per file.",
        )
    return True


def can_add_user(db: Session, organization_id: uuid.UUID) -> bool:
    plan = get_current_plan(db, organization_id)
    users = db.scalar(
        select(func.count()).select_from(OrganizationMember).where(OrganizationMember.organization_id == organization_id)
    ) or 0
    if users >= plan.max_users:
        raise _limit_error(
            plan=plan,
            resource="organization_users",
            limit=plan.max_users,
            used=users,
            message=f"Your {plan.name} plan includes {plan.max_users} organization user(s).",
        )
    return True


def can_add_client_workspace(db: Session, organization_id: uuid.UUID) -> bool:
    get_current_plan(db, organization_id)
    return True


def remaining_reconciliation_runs(db: Session, organization_id: uuid.UUID) -> int:
    plan = get_current_plan(db, organization_id)
    usage = get_current_usage(db, organization_id)
    return max(plan.monthly_run_limit - usage.reconciliation_runs_used, 0)


def remaining_file_capacity(db: Session, organization_id: uuid.UUID) -> int:
    plan = get_current_plan(db, organization_id)
    return plan.max_files_per_run
