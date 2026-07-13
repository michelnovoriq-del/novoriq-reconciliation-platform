from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_environment: str = "development"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/novoriq"
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    upload_dir: str = "uploads"
    storage_backend: str = "local"
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def validate_whop_startup(self) -> None:
        if self.whop_webhook_enabled:
            missing = [
                name
                for name, value in (
                    ("WHOP_WEBHOOK_SECRET", self.whop_webhook_secret),
                    ("WHOP_COMPANY_ID", self.whop_company_id),
                    ("WHOP_PROFESSIONAL_PLAN_ID", self.whop_professional_plan_id),
                    ("WHOP_FIRM_PLAN_ID", self.whop_firm_plan_id),
                )
                if not value
            ]
            if missing:
                raise RuntimeError(f"Missing required Whop webhook configuration: {', '.join(missing)}")
        if self.whop_membership_sync_enabled and not self.whop_api_key:
            raise RuntimeError("Missing required Whop API configuration: WHOP_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
