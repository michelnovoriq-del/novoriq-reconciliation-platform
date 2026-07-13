import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrganizationSubscription, Plan
from app.services.usage_service import get_current_usage


PLAN_DEFINITIONS = {
    "free": {
        "name": "Free Forever",
        "monthly_price_usd": Decimal("0.00"),
        "monthly_run_limit": 2,
        "max_files_per_run": 2,
        "max_rows_per_file": 2500,
        "max_users": 1,
        "max_client_workspaces": 1,
        "detailed_retention_days": 7,
        "features": {
            "core_workflow": True,
            "csv_export": True,
            "basic_audit_history": True,
            "email_support": True,
            "ai_column_mapping": "coming_soon",
            "ai_exception_explanations": "coming_soon",
            "multi_file_reconciliation": "coming_soon",
        },
    },
    "professional": {
        "name": "Professional",
        "monthly_price_usd": Decimal("279.00"),
        "monthly_run_limit": 50,
        "max_files_per_run": 3,
        "max_rows_per_file": 25000,
        "max_users": 3,
        "max_client_workspaces": 20,
        "detailed_retention_days": 365,
        "features": {
            "core_workflow": True,
            "full_audit_history": True,
            "priority_email_support": True,
            "ai_column_mapping": "coming_soon",
            "ai_exception_explanations": "coming_soon",
            "multi_file_reconciliation": "coming_soon",
        },
    },
    "firm": {
        "name": "Firm",
        "monthly_price_usd": Decimal("499.00"),
        "monthly_run_limit": 150,
        "max_files_per_run": 4,
        "max_rows_per_file": 50000,
        "max_users": 10,
        "max_client_workspaces": 75,
        "detailed_retention_days": 730,
        "features": {
            "core_workflow": True,
            "full_audit_history": True,
            "priority_onboarding": True,
            "priority_email_support": True,
            "audit_history_export": "coming_soon",
            "multi_stage_approvals": "coming_soon",
            "three_four_way_reconciliation": "coming_soon",
            "ai_column_mapping": "coming_soon",
            "ai_exception_explanations": "coming_soon",
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly_price_usd": Decimal("799.00"),
        "monthly_run_limit": 400,
        "max_files_per_run": 6,
        "max_rows_per_file": 150000,
        "max_users": 25,
        "max_client_workspaces": 250,
        "detailed_retention_days": 1095,
        "features": {
            "core_workflow": True,
            "full_audit_history": True,
            "priority_onboarding": True,
            "priority_email_support": True,
            "dedicated_success_support": True,
            "audit_history_export": "coming_soon",
            "advanced_approval_workflows": "coming_soon",
            "three_four_way_reconciliation": "coming_soon",
            "ai_column_mapping": "coming_soon",
            "ai_exception_explanations": "coming_soon",
        },
    },
}


def ensure_default_plans(db: Session) -> None:
    for code, definition in PLAN_DEFINITIONS.items():
        plan = db.scalar(select(Plan).where(Plan.code == code))
        if not plan:
            plan = Plan(code=code)
            db.add(plan)
        for field, value in definition.items():
            setattr(plan, field, value)
        plan.is_active = True
    db.flush()


def get_plan_by_code(db: Session, code: str) -> Plan:
    ensure_default_plans(db)
    plan = db.scalar(select(Plan).where(Plan.code == code, Plan.is_active.is_(True)))
    if not plan:
        raise RuntimeError(f"Required plan is missing: {code}")
    return plan


def get_current_plan(db: Session, organization_id: uuid.UUID) -> Plan:
    ensure_default_plans(db)
    subscription = db.scalar(
        select(OrganizationSubscription)
        .join(Plan, Plan.id == OrganizationSubscription.plan_id)
        .where(
            OrganizationSubscription.organization_id == organization_id,
            OrganizationSubscription.status.in_(("active", "trialing")),
        )
    )
    if subscription:
        return subscription.plan
    return ensure_default_free_subscription(db, organization_id).plan


def ensure_default_free_subscription(
    db: Session, organization_id: uuid.UUID
) -> OrganizationSubscription:
    """Repair/provision an organization's free access without replacing paid access."""
    subscription = db.scalar(
        select(OrganizationSubscription).where(
            OrganizationSubscription.organization_id == organization_id
        )
    )
    if subscription:
        get_current_usage(db, organization_id)
        return subscription
    subscription = assign_plan(
        db, organization_id=organization_id, plan_code="free", billing_provider=None
    )
    get_current_usage(db, organization_id)
    return subscription


def assign_plan(
    db: Session,
    *,
    organization_id: uuid.UUID,
    plan_code: str,
    status: str = "active",
    billing_provider: str | None = None,
    external_customer_id: str | None = None,
    external_subscription_id: str | None = None,
    current_period_start=None,
    current_period_end=None,
    cancel_at_period_end: bool | None = None,
) -> OrganizationSubscription:
    plan = get_plan_by_code(db, plan_code)
    subscription = db.scalar(
        select(OrganizationSubscription).where(OrganizationSubscription.organization_id == organization_id)
    )
    if not subscription:
        subscription = OrganizationSubscription(
            organization_id=organization_id,
            plan_id=plan.id,
            status=status,
        )
        db.add(subscription)
    else:
        subscription.plan_id = plan.id
        subscription.status = status
    if billing_provider is not None:
        subscription.billing_provider = billing_provider
    if external_customer_id is not None:
        subscription.external_customer_id = external_customer_id
    if external_subscription_id is not None:
        subscription.external_subscription_id = external_subscription_id
    if current_period_start is not None:
        subscription.current_period_start = current_period_start
    if current_period_end is not None:
        subscription.current_period_end = current_period_end
    if cancel_at_period_end is not None:
        subscription.cancel_at_period_end = cancel_at_period_end
    db.flush()
    return subscription
