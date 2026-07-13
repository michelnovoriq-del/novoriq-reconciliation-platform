import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    organization_name: str = Field(min_length=1, max_length=255)

    @field_validator("organization_name")
    @classmethod
    def organization_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Organization name is required.")
        return value.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RequestEmailVerificationRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=16)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(TokenResponse):
    user: UserResponse
    organization: dict | None = None
    plan: dict | None = None
    entitlements: dict | None = None
