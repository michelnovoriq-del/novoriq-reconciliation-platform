from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    OrganizationMember,
    OrganizationSubscription,
    PendingWhopMembershipLink,
    User,
    WhopMembershipLink,
    WhopWebhookEvent,
)
from app.models.base import utc_now
from app.services.audit_service import create_audit_log
from app.services.email_normalization import normalize_email
from app.services.email_service import send_plan_activation_email, send_plan_downgrade_email
from app.services.plan_service import assign_plan
from app.services.whop_plan_mapping_service import map_whop_plan_to_novoriq_plan


ACTIVE_MEMBERSHIP_STATUSES = {"active", "trialing", "completed"}


def _first_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data
        for part in key.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if value is not None:
            return value
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=utc_now().tzinfo)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _extract_membership(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    user = data.get("user") if isinstance(data.get("user"), dict) else {}
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
    product = data.get("product") if isinstance(data.get("product"), dict) else {}
    company = data.get("company") if isinstance(data.get("company"), dict) else {}
    return {
        "membership_id": _first_value(data, "membership_id", "id"),
        "status": _first_value(data, "status", "membership_status") or "unknown",
        "whop_user_id": _first_value(data, "user_id", "whop_user_id", "user.id") or _first_value(user, "id"),
        "whop_username": _first_value(data, "username", "user.username") or _first_value(user, "username"),
        "whop_member_id": _first_value(data, "member_id", "member.id"),
        "email": _first_value(data, "email", "user.email") or _first_value(user, "email"),
        "plan_id": _first_value(data, "plan_id", "plan.id") or _first_value(plan, "id"),
        "product_id": _first_value(data, "product_id", "product.id", "access_pass_id") or _first_value(product, "id"),
        "company_id": _first_value(data, "company_id", "company.id") or _first_value(company, "id"),
        "manage_url": _first_value(data, "manage_url", "manage_membership_url"),
        "period_start": _parse_datetime(_first_value(data, "current_period_start", "renewal_period_start")),
        "period_end": _parse_datetime(_first_value(data, "current_period_end", "renewal_period_end")),
        "cancel_at_period_end": bool(_first_value(data, "cancel_at_period_end") or False),
    }


def _create_or_update_pending(
    db: Session,
    *,
    membership: dict[str, Any],
    event: WhopWebhookEvent | None,
    reason: str,
) -> PendingWhopMembershipLink:
    pending = db.scalar(
        select(PendingWhopMembershipLink).where(
            PendingWhopMembershipLink.whop_membership_id == membership["membership_id"]
        )
    )
    if not pending:
        pending = PendingWhopMembershipLink(
            whop_membership_id=membership["membership_id"],
            whop_user_id=membership["whop_user_id"],
            whop_email_normalized=normalize_email(membership["email"] or ""),
            whop_plan_id=membership["plan_id"] or "",
            whop_product_id=membership["product_id"],
            membership_status=membership["status"],
            raw_event_id=event.id if event else None,
            reason=reason,
        )
        db.add(pending)
    else:
        pending.membership_status = membership["status"]
        pending.reason = reason
        pending.raw_event_id = event.id if event else pending.raw_event_id
    return pending


def _activate_link(db: Session, *, link: WhopMembershipLink, membership: dict[str, Any], plan_code: str) -> None:
    now = utc_now()
    first_activation = link.activated_at is None or link.mapped_plan_code != plan_code
    link.whop_company_id = membership["company_id"]
    link.whop_username = membership["whop_username"]
    link.whop_member_id = membership["whop_member_id"]
    link.whop_plan_id = membership["plan_id"]
    link.whop_product_id = membership["product_id"]
    link.whop_manage_url = membership["manage_url"]
    link.membership_status = membership["status"]
    link.mapped_plan_code = plan_code
    link.current_period_start = membership["period_start"]
    link.current_period_end = membership["period_end"]
    link.cancel_at_period_end = membership["cancel_at_period_end"]
    link.activated_at = link.activated_at or now
    link.deactivated_at = None
    link.last_verified_at = now
    assign_plan(
        db,
        organization_id=link.organization_id,
        plan_code=plan_code,
        status="active",
        billing_provider="whop",
        external_customer_id=link.whop_user_id,
        external_subscription_id=link.whop_membership_id,
        current_period_start=link.current_period_start,
        current_period_end=link.current_period_end,
        cancel_at_period_end=link.cancel_at_period_end,
    )
    create_audit_log(
        db,
        organization_id=link.organization_id,
        user_id=link.novoriq_user_id,
        action="plan_activated",
        entity_type="whop_membership_link",
        entity_id=link.id,
        metadata={"plan_code": plan_code},
    )
    if first_activation:
        send_plan_activation_email(to_email=link.whop_email_normalized, plan_name=plan_code.title())


def process_pending_membership_for_user(
    db: Session, *, pending_link: PendingWhopMembershipLink, user: User
) -> bool:
    membership = {
        "membership_id": pending_link.whop_membership_id,
        "status": pending_link.membership_status,
        "whop_user_id": pending_link.whop_user_id,
        "whop_username": None,
        "whop_member_id": None,
        "email": pending_link.whop_email_normalized,
        "plan_id": pending_link.whop_plan_id,
        "product_id": pending_link.whop_product_id,
        "company_id": None,
        "manage_url": None,
        "period_start": None,
        "period_end": None,
        "cancel_at_period_end": False,
    }
    plan_code = map_whop_plan_to_novoriq_plan(pending_link.whop_plan_id, pending_link.whop_product_id)
    if not plan_code:
        return False
    linked = _link_membership_to_user(db, membership=membership, user=user, plan_code=plan_code)
    if linked:
        pending_link.resolved_at = utc_now()
        pending_link.resolution = "linked_after_email_verification"
    return linked


def _link_membership_to_user(db: Session, *, membership: dict[str, Any], user: User, plan_code: str) -> bool:
    if not user.email_verified_at:
        return False
    member = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id, OrganizationMember.role.in_(("owner", "admin")))
        .order_by(OrganizationMember.created_at.asc())
    )
    if not member:
        return False
    conflict = db.scalar(
        select(WhopMembershipLink).where(
            WhopMembershipLink.whop_user_id == membership["whop_user_id"],
            WhopMembershipLink.organization_id != member.organization_id,
        )
    )
    if conflict:
        return False
    link = WhopMembershipLink(
        organization_id=member.organization_id,
        novoriq_user_id=user.id,
        whop_company_id=membership["company_id"],
        whop_user_id=membership["whop_user_id"],
        whop_username=membership["whop_username"],
        whop_member_id=membership["whop_member_id"],
        whop_membership_id=membership["membership_id"],
        whop_plan_id=membership["plan_id"],
        whop_product_id=membership["product_id"],
        whop_manage_url=membership["manage_url"],
        membership_status=membership["status"],
        mapped_plan_code=plan_code,
        whop_email_normalized=normalize_email(membership["email"] or user.email),
        current_period_start=membership["period_start"],
        current_period_end=membership["period_end"],
        cancel_at_period_end=membership["cancel_at_period_end"],
    )
    db.add(link)
    db.flush()
    _activate_link(db, link=link, membership=membership, plan_code=plan_code)
    create_audit_log(
        db,
        organization_id=member.organization_id,
        user_id=user.id,
        action="whop_membership_linked",
        entity_type="whop_membership_link",
        entity_id=link.id,
        metadata={"whop_membership_id": link.whop_membership_id},
    )
    return True


def process_membership_event(db: Session, *, payload: dict[str, Any], event: WhopWebhookEvent) -> None:
    membership = _extract_membership(payload)
    if not membership["membership_id"] or not membership["whop_user_id"]:
        event.processing_status = "ignored"
        event.error_code = "missing_membership_identity"
        event.processed_at = utc_now()
        return

    plan_code = map_whop_plan_to_novoriq_plan(membership["plan_id"], membership["product_id"])
    if not plan_code:
        _create_or_update_pending(db, membership=membership, event=event, reason="unknown_plan")
        event.processing_status = "ignored"
        event.error_code = "unknown_plan"
        event.processed_at = utc_now()
        return

    existing_link = db.scalar(
        select(WhopMembershipLink).where(WhopMembershipLink.whop_membership_id == membership["membership_id"])
    )
    event_type = event.webhook_type
    if event_type in {"membership.deactivated", "membership.deleted"}:
        if existing_link:
            existing_link.membership_status = membership["status"]
            existing_link.deactivated_at = utc_now()
            assign_plan(
                db,
                organization_id=existing_link.organization_id,
                plan_code="free",
                status="inactive",
                billing_provider="whop",
                external_customer_id=existing_link.whop_user_id,
                external_subscription_id=existing_link.whop_membership_id,
                current_period_end=membership["period_end"],
            )
            create_audit_log(
                db,
                organization_id=existing_link.organization_id,
                user_id=existing_link.novoriq_user_id,
                action="plan_downgraded",
                entity_type="whop_membership_link",
                entity_id=existing_link.id,
            )
            send_plan_downgrade_email(to_email=existing_link.whop_email_normalized)
        event.processing_status = "processed"
        event.processed_at = utc_now()
        return

    if existing_link:
        if event_type == "membership.cancel_at_period_end_changed":
            existing_link.cancel_at_period_end = membership["cancel_at_period_end"]
            subscription = db.scalar(
                select(OrganizationSubscription).where(
                    OrganizationSubscription.organization_id == existing_link.organization_id
                )
            )
            if subscription:
                subscription.cancel_at_period_end = membership["cancel_at_period_end"]
                subscription.current_period_end = membership["period_end"] or subscription.current_period_end
            create_audit_log(
                db,
                organization_id=existing_link.organization_id,
                user_id=existing_link.novoriq_user_id,
                action="whop_cancel_at_period_end_changed",
                entity_type="whop_membership_link",
                entity_id=existing_link.id,
            )
        elif str(membership["status"]).lower() in ACTIVE_MEMBERSHIP_STATUSES:
            _activate_link(db, link=existing_link, membership=membership, plan_code=plan_code)
        event.processing_status = "processed"
        event.processed_at = utc_now()
        return

    email = normalize_email(membership["email"] or "")
    users = db.scalars(select(User).where(func.lower(User.email) == email, User.is_active.is_(True))).all()
    if len(users) != 1:
        _create_or_update_pending(
            db,
            membership=membership,
            event=event,
            reason="no_matching_user" if not users else "multiple_matches",
        )
    elif not users[0].email_verified_at:
        _create_or_update_pending(db, membership=membership, event=event, reason="email_not_verified")
    elif not _link_membership_to_user(db, membership=membership, user=users[0], plan_code=plan_code):
        _create_or_update_pending(db, membership=membership, event=event, reason="user_not_owner_or_admin")
    event.processing_status = "processed"
    event.processed_at = utc_now()
