from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, OrganizationMember, User
from app.models.base import utc_now
from app.schemas.auth import LoginRequest, RegisterRequest
from app.security import create_access_token, hash_password, verify_password
from app.services.audit_service import create_audit_log
from app.services.email_normalization import normalize_email
from app.services.plan_service import ensure_default_free_subscription


def register_user(db: Session, payload: RegisterRequest) -> tuple[User, str]:
    normalized_email = normalize_email(str(payload.email))
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    try:
        user = User(
            email=normalized_email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            email_verified_at=utc_now(),
        )
        organization = Organization(name=payload.organization_name.strip())
        db.add_all([user, organization])
        db.flush()
        subscription = ensure_default_free_subscription(db, organization.id)
        db.add(OrganizationMember(user_id=user.id, organization_id=organization.id, role="owner"))
        for action, entity_type, entity_id in (
            ("account_registered", "user", user.id),
            ("organization_created", "organization", organization.id),
            ("free_plan_assigned", "organization_subscription", subscription.id),
        ):
            create_audit_log(db, organization_id=organization.id, user_id=user.id,
                             action=action, entity_type=entity_type, entity_id=entity_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user, create_access_token(str(user.id))


def authenticate_user(db: Session, payload: LoginRequest) -> tuple[User, str]:
    user = db.scalar(select(User).where(User.email == normalize_email(str(payload.email))))
    if not user or not verify_password(payload.password, user.hashed_password):
        if user:
            # Avoid logging attempted passwords or other request secrets.
            membership = user.organization_memberships[0] if user.organization_memberships else None
            if membership:
                create_audit_log(
                    db,
                    organization_id=membership.organization_id,
                    user_id=user.id,
                    action="login_failed",
                    entity_type="user",
                    entity_id=user.id,
                )
                db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive."
        )
    membership = user.organization_memberships[0] if user.organization_memberships else None
    if membership:
        ensure_default_free_subscription(db, membership.organization_id)
        create_audit_log(
            db,
            organization_id=membership.organization_id,
            user_id=user.id,
            action="login_succeeded",
            entity_type="user",
            entity_id=user.id,
        )
        db.commit()
    return user, create_access_token(str(user.id))
