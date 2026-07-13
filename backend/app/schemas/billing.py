from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
import uuid


class PlanResponse(BaseModel):
    code: str
    name: str
    monthly_price_usd: Decimal
    monthly_run_limit: int
    max_files_per_run: int
    max_rows_per_file: int
    max_users: int
    max_client_workspaces: int
    detailed_retention_days: int
    features: dict

    model_config = {"from_attributes": True}


class UsageResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    reconciliation_runs_used: int
    files_uploaded: int
    rows_processed: int
    exports_generated: int

    model_config = {"from_attributes": True}


class CurrentEntitlementsResponse(BaseModel):
    plan: PlanResponse
    usage: UsageResponse
    remaining_reconciliation_runs: int
    remaining_file_capacity: int


class BillingStatusResponse(BaseModel):
    plan_code: str
    plan_name: str
    subscription_status: str
    billing_provider: str | None = None
    whop_linked: bool = False
    pending_whop_link: bool = False
    pending_reason: str | None = None
    manage_url: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    message: str | None = None


class BootstrapUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    email_verified: bool
    role: str


class BootstrapOrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str


class BootstrapSubscriptionResponse(BaseModel):
    plan_code: str
    plan_name: str
    status: str
    billing_provider: str | None = None
    current_period_end: datetime | None = None


class BootstrapUsageResponse(BaseModel):
    reconciliation_runs_used: int
    reconciliation_runs_limit: int
    remaining_reconciliation_runs: int
    files_uploaded: int
    rows_processed: int
    reset_at: datetime


class BootstrapEntitlementsResponse(BaseModel):
    max_files_per_run: int
    max_rows_per_file: int
    max_users: int
    max_client_workspaces: int
    detailed_retention_days: int


class BootstrapBillingResponse(BaseModel):
    membership_linked: bool
    whop_status: str | None = None
    pending_action: bool = False


class AccountBootstrapResponse(BaseModel):
    user: BootstrapUserResponse
    organization: BootstrapOrganizationResponse
    subscription: BootstrapSubscriptionResponse
    usage: BootstrapUsageResponse
    entitlements: BootstrapEntitlementsResponse
    billing: BootstrapBillingResponse
