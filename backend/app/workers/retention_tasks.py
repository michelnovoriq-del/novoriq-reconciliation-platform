from app.database import SessionLocal
from app.services.retention_service import cleanup_expired_raw_files, cleanup_expired_reconciliation_data


def cleanup_expired_exports() -> dict:
    return {"exports_deleted": 0, "note": "Generated exports are streamed and not persisted in this MVP."}


def retry_failed_storage_deletions() -> dict:
    return {"retry_count": 0, "note": "Storage deletion retries use the same idempotent cleanup task."}


def run_daily_retention_cleanup() -> dict:
    with SessionLocal() as db:
        raw_files = cleanup_expired_raw_files(db)
    with SessionLocal() as db:
        reconciliation_data = cleanup_expired_reconciliation_data(db)
    return {
        "raw_files": raw_files,
        "exports": cleanup_expired_exports(),
        "reconciliation_data": reconciliation_data,
        "retries": retry_failed_storage_deletions(),
    }
