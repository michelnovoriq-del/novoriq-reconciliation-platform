import base64
import hashlib
import hmac
import json
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import WhopWebhookEvent
from app.models.base import utc_now
from app.services.whop_membership_service import process_membership_event


def _decode_secret(secret: str) -> bytes:
    cleaned = secret.removeprefix("whsec_")
    try:
        return base64.b64decode(cleaned)
    except Exception:
        return secret.encode("utf-8")


def _signature_candidates(signature_header: str) -> list[str]:
    candidates: list[str] = []
    for part in signature_header.split():
        for value in part.split(","):
            value = value.strip()
            if not value:
                continue
            candidates.append(value.split("=", 1)[1] if value.startswith("v1=") else value)
    return candidates


def verify_whop_signature(*, raw_body: bytes, headers: dict[str, str]) -> None:
    settings = get_settings()
    if not settings.whop_webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Whop webhook is not configured.")
    webhook_id = headers.get("webhook-id") or headers.get("whop-webhook-id")
    timestamp = headers.get("webhook-timestamp") or headers.get("whop-webhook-timestamp")
    signature = headers.get("webhook-signature") or headers.get("whop-webhook-signature")
    if not webhook_id or not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Whop webhook signature.")
    signed_payload = f"{webhook_id}.{timestamp}.".encode("utf-8") + raw_body
    digest = hmac.new(_decode_secret(settings.whop_webhook_secret), signed_payload, hashlib.sha256).digest()
    expected_hex = digest.hex()
    expected_b64 = base64.b64encode(digest).decode("utf-8")
    if not any(
        hmac.compare_digest(candidate, expected_hex) or hmac.compare_digest(candidate, expected_b64)
        for candidate in _signature_candidates(signature)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Whop webhook signature.")


def _event_id(payload: dict[str, Any], headers: dict[str, str]) -> str:
    return (
        str(payload.get("id") or payload.get("event_id") or headers.get("webhook-id") or "")
        or hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    )


def _event_type(payload: dict[str, Any]) -> str:
    return str(payload.get("type") or payload.get("event") or payload.get("webhook_type") or "unknown")


def _company_id(payload: dict[str, Any]) -> str | None:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    company = data.get("company") if isinstance(data.get("company"), dict) else {}
    value = data.get("company_id") or company.get("id") or payload.get("company_id")
    return str(value) if value else None


def _membership_id(payload: dict[str, Any]) -> str | None:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    value = data.get("membership_id") or data.get("id")
    return str(value) if value else None


async def receive_whop_webhook(db: Session, request: Request) -> dict[str, str]:
    raw_body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    verify_whop_signature(raw_body=raw_body, headers=headers)
    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload.")

    settings = get_settings()
    company_id = _company_id(payload)
    if settings.whop_company_id and company_id != settings.whop_company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook company does not match.")

    whop_event_id = _event_id(payload, headers)
    existing = db.scalar(select(WhopWebhookEvent).where(WhopWebhookEvent.whop_event_id == whop_event_id))
    if existing and existing.processing_status in {"processed", "ignored"}:
        return {"status": "ok"}

    event = existing or WhopWebhookEvent(
        whop_event_id=whop_event_id,
        webhook_type=_event_type(payload),
        whop_company_id=company_id,
        whop_membership_id=_membership_id(payload),
        payload_hash=hashlib.sha256(raw_body).hexdigest(),
        processing_status="received",
        received_at=utc_now(),
    )
    if not existing:
        db.add(event)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            return {"status": "ok"}

    event.processing_status = "processing"
    event.attempt_count += 1
    if event.webhook_type.startswith("membership."):
        process_membership_event(db, payload=payload, event=event)
    else:
        event.processing_status = "ignored"
        event.processed_at = utc_now()
    db.commit()
    return {"status": "ok"}
