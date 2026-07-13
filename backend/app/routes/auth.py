from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services.plan_service import get_current_plan
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    RequestEmailVerificationRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import authenticate_user, register_user
from app.services.email_verification_service import request_email_verification, verify_email


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user, token = register_user(db, payload)
    membership = user.organization_memberships[0]
    plan = get_current_plan(db, membership.organization_id)
    organization = membership.organization
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        organization={"id": str(organization.id), "name": organization.name},
        plan={"code": plan.code, "name": plan.name},
        entitlements={"monthly_reconciliation_run_limit": plan.monthly_run_limit,
                      "max_files_per_run": plan.max_files_per_run,
                      "max_rows_per_file": plan.max_rows_per_file, "max_users": plan.max_users,
                      "max_client_workspaces": plan.max_client_workspaces},
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _, token = authenticate_user(db, payload)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/request-email-verification")
def request_verification(payload: RequestEmailVerificationRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    request_email_verification(db, str(payload.email))
    return {"status": "ok"}


@router.post("/verify-email")
def verify_email_token(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    verify_email(db, payload.token)
    return {"status": "ok"}
