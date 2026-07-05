from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, OrganizationMember, User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.security import create_access_token, hash_password, verify_password


def register_user(db: Session, payload: RegisterRequest) -> tuple[User, str]:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    organization = Organization(name=payload.organization_name)
    db.add_all([user, organization])
    db.flush()
    db.add(
        OrganizationMember(user_id=user.id, organization_id=organization.id, role="owner")
    )
    db.commit()
    db.refresh(user)
    return user, create_access_token(str(user.id))


def authenticate_user(db: Session, payload: LoginRequest) -> tuple[User, str]:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive."
        )
    return user, create_access_token(str(user.id))
