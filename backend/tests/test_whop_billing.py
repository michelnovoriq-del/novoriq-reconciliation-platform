import base64
import hashlib
import hmac

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.config import get_settings
from app.main import app
from app.services.plan_service import PLAN_DEFINITIONS
from app.services.whop_plan_mapping_service import map_whop_plan_to_novoriq_plan
from app.services.whop_webhook_service import verify_whop_signature


def test_billing_and_whop_routes_are_registered() -> None:
    methods_by_path = {
        route.path: route.methods for route in app.routes if isinstance(route, APIRoute)
    }
    assert "GET" in methods_by_path["/billing/status"]
    assert "GET" in methods_by_path["/account/bootstrap"]
    assert "POST" in methods_by_path["/billing/sync-whop-access"]
    assert "POST" in methods_by_path["/webhooks/whop"]
    assert "POST" in methods_by_path["/auth/request-email-verification"]
    assert "POST" in methods_by_path["/auth/verify-email"]


def test_enterprise_plan_is_seeded_at_799() -> None:
    assert PLAN_DEFINITIONS["enterprise"]["monthly_price_usd"].to_eng_string() == "799.00"
    assert PLAN_DEFINITIONS["enterprise"]["monthly_run_limit"] > PLAN_DEFINITIONS["firm"]["monthly_run_limit"]


def test_whop_plan_mapping_uses_configured_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "whop_professional_plan_id", "plan_pro")
    monkeypatch.setattr(settings, "whop_firm_plan_id", "plan_firm")
    monkeypatch.setattr(settings, "whop_enterprise_plan_id", "plan_ent")
    assert map_whop_plan_to_novoriq_plan("plan_pro") == "professional"
    assert map_whop_plan_to_novoriq_plan("plan_firm") == "firm"
    assert map_whop_plan_to_novoriq_plan("plan_ent") == "enterprise"
    assert map_whop_plan_to_novoriq_plan("unknown") is None


def test_whop_signature_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    secret = base64.b64encode(b"test-secret").decode("utf-8")
    monkeypatch.setattr(settings, "whop_webhook_secret", f"whsec_{secret}")
    raw_body = b'{"type":"membership.activated"}'
    signed_payload = b"evt_1.123." + raw_body
    digest = hmac.new(b"test-secret", signed_payload, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode("utf-8")
    verify_whop_signature(
        raw_body=raw_body,
        headers={
            "webhook-id": "evt_1",
            "webhook-timestamp": "123",
            "webhook-signature": f"v1,{signature}",
        },
    )
    with pytest.raises(HTTPException):
        verify_whop_signature(
            raw_body=raw_body,
            headers={
                "webhook-id": "evt_1",
                "webhook-timestamp": "123",
                "webhook-signature": "v1,bad",
            },
        )
