from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_active_organization, get_current_user
from app.models import (Organization, OrganizationMember, OrganizationSubscription,
                        PendingWhopMembershipLink, User, WhopMembershipLink)
from app.schemas.billing import AccountBootstrapResponse
from app.services.email_normalization import normalize_email
from app.services.plan_service import ensure_default_free_subscription
from app.services.usage_service import get_current_usage

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/bootstrap", response_model=AccountBootstrapResponse)
def bootstrap(db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
              organization: Organization = Depends(get_active_organization)) -> dict:
    subscription = ensure_default_free_subscription(db, organization.id)
    usage = get_current_usage(db, organization.id)
    plan = subscription.plan
    member = db.scalar(select(OrganizationMember).where(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.user_id == current_user.id))
    link = db.scalar(select(WhopMembershipLink).where(WhopMembershipLink.organization_id == organization.id))
    pending = db.scalar(select(PendingWhopMembershipLink).where(
        PendingWhopMembershipLink.whop_email_normalized == normalize_email(current_user.email),
        PendingWhopMembershipLink.resolved_at.is_(None)))
    db.commit()
    return {
        "user": {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name,
                 "email_verified": current_user.email_verified_at is not None,
                 "role": member.role if member else "member"},
        "organization": {"id": organization.id, "name": organization.name},
        "subscription": {"plan_code": plan.code, "plan_name": plan.name, "status": subscription.status,
                         "billing_provider": subscription.billing_provider,
                         "current_period_end": subscription.current_period_end},
        "usage": {"reconciliation_runs_used": usage.reconciliation_runs_used,
                  "reconciliation_runs_limit": plan.monthly_run_limit,
                  "remaining_reconciliation_runs": max(plan.monthly_run_limit - usage.reconciliation_runs_used, 0),
                  "files_uploaded": usage.files_uploaded, "rows_processed": usage.rows_processed,
                  "reset_at": usage.period_end},
        "entitlements": {"max_files_per_run": plan.max_files_per_run,
                         "max_rows_per_file": plan.max_rows_per_file, "max_users": plan.max_users,
                         "max_client_workspaces": plan.max_client_workspaces,
                         "detailed_retention_days": plan.detailed_retention_days},
        "billing": {"membership_linked": bool(link),
                    "whop_status": link.membership_status if link else None,
                    "pending_action": bool(pending)},
    }
