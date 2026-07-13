import hashlib
import secrets
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PendingWhopMembershipLink, User
from app.models.base import utc_now
from app.services.email_normalization import normalize_email
from app.services.email_service import send_email_verification
from app.services.whop_membership_service import process_pending_membership_for_user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def request_email_verification(db: Session, email: str) -> None:
    normalized = normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized))
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        user.email_verification_token_hash = _hash_token(token)
        user.email_verification_expires_at = utc_now() + timedelta(hours=24)
        send_email_verification(to_email=user.email, token=token)
    db.commit()


def verify_email(db: Session, token: str) -> None:
    token_hash = _hash_token(token)
    user = db.scalar(select(User).where(User.email_verification_token_hash == token_hash))
    if not user or not user.email_verification_expires_at or user.email_verification_expires_at < utc_now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token.")

    user.email_verified_at = utc_now()
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    pending_links = db.scalars(
        select(PendingWhopMembershipLink).where(
            PendingWhopMembershipLink.whop_email_normalized == user.email,
            PendingWhopMembershipLink.resolved_at.is_(None),
        )
    ).all()
    for pending_link in pending_links:
        process_pending_membership_for_user(db, pending_link=pending_link, user=user)
    db.commit()
