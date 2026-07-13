from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_active_organization, get_current_user
from app.models import Organization, OrganizationSubscription, PendingWhopMembershipLink, User, WhopMembershipLink
from app.schemas.billing import BillingStatusResponse, CurrentEntitlementsResponse
from app.services.entitlement_service import remaining_file_capacity, remaining_reconciliation_runs
from app.services.email_normalization import normalize_email
from app.services.plan_service import get_current_plan
from app.services.usage_service import get_current_usage


router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/current", response_model=CurrentEntitlementsResponse)
def current_entitlements(
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_active_organization),
) -> CurrentEntitlementsResponse:
    plan = get_current_plan(db, organization.id)
    usage = get_current_usage(db, organization.id)
    db.commit()
    return CurrentEntitlementsResponse(
        plan=plan,
        usage=usage,
        remaining_reconciliation_runs=remaining_reconciliation_runs(db, organization.id),
        remaining_file_capacity=remaining_file_capacity(db, organization.id),
    )


@router.get("/status", response_model=BillingStatusResponse)
def billing_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_active_organization),
) -> BillingStatusResponse:
    plan = get_current_plan(db, organization.id)
    subscription = db.scalar(
        select(OrganizationSubscription).where(OrganizationSubscription.organization_id == organization.id)
    )
    link = db.scalar(select(WhopMembershipLink).where(WhopMembershipLink.organization_id == organization.id))
    pending = db.scalar(
        select(PendingWhopMembershipLink).where(
            PendingWhopMembershipLink.whop_email_normalized == normalize_email(current_user.email),
            PendingWhopMembershipLink.resolved_at.is_(None),
        )
    )
    message = None
    if pending:
        message = "Payment was received, but Novoriq could not automatically link the membership. Verify your account email or contact support."
    elif link and link.cancel_at_period_end and link.current_period_end:
        message = f"Your {plan.name} plan remains active until {link.current_period_end.date().isoformat()}."
    return BillingStatusResponse(
        plan_code=plan.code,
        plan_name=plan.name,
        subscription_status=subscription.status if subscription else "active",
        billing_provider=subscription.billing_provider if subscription else None,
        whop_linked=bool(link),
        pending_whop_link=bool(pending),
        pending_reason=pending.reason if pending else None,
        manage_url=link.whop_manage_url if link else None,
        current_period_end=subscription.current_period_end if subscription else None,
        cancel_at_period_end=subscription.cancel_at_period_end if subscription else False,
        message=message,
    )


@router.post("/sync-whop-access", response_model=BillingStatusResponse)
def sync_whop_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_active_organization),
) -> BillingStatusResponse:
    return billing_status(db=db, current_user=current_user, organization=organization)
