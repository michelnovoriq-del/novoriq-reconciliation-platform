import uuid
from calendar import monthrange
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UsagePeriod


def current_utc_period(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    _, last_day = monthrange(now.year, now.month)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return start, end


def get_current_usage(db: Session, organization_id: uuid.UUID, *, lock: bool = False) -> UsagePeriod:
    period_start, period_end = current_utc_period()
    statement = select(UsagePeriod).where(
        UsagePeriod.organization_id == organization_id,
        UsagePeriod.period_start == period_start,
        UsagePeriod.period_end == period_end,
    )
    if lock:
        statement = statement.with_for_update()
    usage = db.scalar(statement)
    if not usage:
        usage = UsagePeriod(
            organization_id=organization_id,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(usage)
        db.flush()
        if lock:
            usage = db.scalar(statement) or usage
    return usage


def increment_reconciliation_usage(db: Session, organization_id: uuid.UUID) -> UsagePeriod:
    usage = get_current_usage(db, organization_id, lock=True)
    usage.reconciliation_runs_used += 1
    db.flush()
    return usage


def increment_upload_usage(db: Session, organization_id: uuid.UUID, *, rows_processed: int = 0) -> UsagePeriod:
    usage = get_current_usage(db, organization_id, lock=True)
    usage.files_uploaded += 1
    usage.rows_processed += rows_processed
    db.flush()
    return usage


def increment_export_usage(db: Session, organization_id: uuid.UUID) -> UsagePeriod:
    usage = get_current_usage(db, organization_id, lock=True)
    usage.exports_generated += 1
    db.flush()
    return usage
