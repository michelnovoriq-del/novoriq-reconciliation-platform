from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PRODUCTION_FRONTEND_ORIGIN = "https://agenticreconcilliation.netlify.app"
PRODUCTION_BACKEND_HOST = "novoriq-reconciliation-platform.onrender.com"
WEAK_JWT_SECRETS = {
    "change-this-in-production",
    "changeme",
    "secret",
    "your-secret-key",
    "replace-me",
}


class Settings(BaseSettings):
    app_environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/novoriq"
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    backend_public_url: str | None = None
    # Any is intentional: pydantic-settings 2.3 JSON-decodes list fields before
    # field validators, which made the documented comma-separated format fail.
    backend_cors_origins: Any = Field(default_factory=list)
    allowed_hosts: Any = Field(default_factory=list)
    upload_dir: str = "uploads"
    storage_backend: str = "local"
    allow_ephemeral_test_uploads: bool = False
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_bucket_name: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_use_ssl: bool = True
    s3_signed_url_ttl_seconds: int = 300
    max_upload_size_mb_free: int = 15
    max_upload_size_mb_professional: int = 50
    max_upload_size_mb_firm: int = 100
    max_upload_size_mb_enterprise: int = 250
    malware_scanning_enabled: bool = False
    frontend_url: str = "http://localhost:3000"
    support_email: str = "michelnovoriq@gmail.com"
    whop_api_key: str | None = None
    whop_webhook_secret: str | None = None
    whop_company_id: str | None = None
    whop_professional_plan_id: str | None = None
    whop_firm_plan_id: str | None = None
    whop_enterprise_plan_id: str | None = None
    whop_professional_product_id: str | None = None
    whop_firm_product_id: str | None = None
    whop_enterprise_product_id: str | None = None
    whop_api_base_url: str = "https://api.whop.com/api/v1"
    whop_webhook_enabled: bool = True
    whop_membership_sync_enabled: bool = True
    whop_webhook_raw_payload_logging: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", populate_by_name=True
    )

    @field_validator("backend_cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_list_setting(cls, value: Any) -> Any:
        """Accept JSON arrays (preferred) or a legacy comma-separated list."""
        if value is None or isinstance(value, list):
            return value or []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                import json

                parsed = json.loads(stripped)
                if not isinstance(parsed, list):
                    raise ValueError("List settings must be a JSON array or comma-separated list")
                return parsed
            return [item.strip() for item in stripped.split(",") if item.strip()]
        raise ValueError("List settings must be a JSON array or comma-separated list")

    @field_validator("backend_cors_origins")
    @classmethod
    def normalize_cors_origins(cls, value: list[Any]) -> list[str]:
        origins: list[str] = []
        for raw in value:
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("CORS origins cannot contain empty or non-string values")
            origin = raw.strip().rstrip("/")
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid CORS origin: {raw!r}")
            if parsed.path or parsed.params or parsed.query or parsed.fragment or parsed.username or parsed.password:
                raise ValueError(f"CORS origins must contain only scheme and host: {raw!r}")
            if origin not in origins:
                origins.append(origin)
        return origins

    @field_validator("allowed_hosts")
    @classmethod
    def normalize_allowed_hosts(cls, value: list[Any]) -> list[str]:
        hosts: list[str] = []
        for raw in value:
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("Allowed hosts cannot contain empty or non-string values")
            host = raw.strip().lower().rstrip(".")
            if "://" in host or "/" in host or any(char.isspace() for char in host):
                raise ValueError(f"Invalid allowed host: {raw!r}")
            if host not in hosts:
                hosts.append(host)
        return hosts

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_setting(cls, value: Any) -> Any:
        # Some hosting/build environments use DEBUG=release rather than a boolean.
        if isinstance(value, str) and value.lower() in {"release", "production"}:
            return False
        return value

    @property
    def is_production(self) -> bool:
        return self.app_environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        if self.backend_cors_origins:
            return self.backend_cors_origins
        if self.is_production:
            return []
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def trusted_hosts(self) -> list[str]:
        if self.allowed_hosts:
            return self.allowed_hosts
        return [] if self.is_production else ["localhost", "127.0.0.1", "testserver"]

    def validate_production(self) -> None:
        if not self.is_production:
            return
        errors: list[str] = []
        if self.debug:
            errors.append("DEBUG must be disabled")
        if not self.database_url:
            errors.append("DATABASE_URL is required")
        if not self.jwt_secret_key or self.jwt_secret_key.lower() in WEAK_JWT_SECRETS or len(self.jwt_secret_key) < 32:
            errors.append("JWT_SECRET_KEY must be a non-placeholder value of at least 32 characters")
        if not self.frontend_url:
            errors.append("FRONTEND_URL is required")
        elif self.frontend_url != PRODUCTION_FRONTEND_ORIGIN:
            errors.append(f"FRONTEND_URL must equal {PRODUCTION_FRONTEND_ORIGIN}")
        if not self.backend_public_url:
            errors.append("BACKEND_PUBLIC_URL is required")
        elif urlparse(self.backend_public_url).scheme != "https":
            errors.append("BACKEND_PUBLIC_URL must use HTTPS")
        if self.cors_origins != [PRODUCTION_FRONTEND_ORIGIN]:
            errors.append(f"BACKEND_CORS_ORIGINS must contain only {PRODUCTION_FRONTEND_ORIGIN}")
        if "*" in self.cors_origins:
            errors.append("BACKEND_CORS_ORIGINS cannot contain a wildcard")
        if self.trusted_hosts != [PRODUCTION_BACKEND_HOST]:
            errors.append(f"ALLOWED_HOSTS must contain only {PRODUCTION_BACKEND_HOST}")
        if "*" in self.trusted_hosts:
            errors.append("ALLOWED_HOSTS cannot contain a wildcard")
        if not self.support_email or "@" not in self.support_email:
            errors.append("SUPPORT_EMAIL is required")
        if self.storage_backend not in {"local", "s3"}:
            errors.append("STORAGE_BACKEND must be local or s3")
        if self.storage_backend == "s3" and not all(
            (self.s3_bucket_name, self.s3_access_key_id, self.s3_secret_access_key)
        ):
            errors.append("S3 storage credentials and bucket are required for STORAGE_BACKEND=s3")
        if errors:
            raise RuntimeError("Invalid production configuration: " + "; ".join(errors))

    def validate_whop_startup(self) -> None:
        if self.whop_webhook_enabled:
            missing = [name for name, value in (("WHOP_WEBHOOK_SECRET", self.whop_webhook_secret), ("WHOP_COMPANY_ID", self.whop_company_id), ("WHOP_PROFESSIONAL_PLAN_ID", self.whop_professional_plan_id), ("WHOP_FIRM_PLAN_ID", self.whop_firm_plan_id)) if not value]
            if missing:
                raise RuntimeError(f"Missing required Whop webhook configuration: {', '.join(missing)}")
        if self.whop_membership_sync_enabled and not self.whop_api_key:
            raise RuntimeError("Missing required Whop API configuration: WHOP_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
