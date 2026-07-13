from dataclasses import dataclass, asdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import MatchResult, ReconciliationRun, UploadedFile
from app.models.base import utc_now
from app.services.storage import get_storage_backend


@dataclass
class CleanupReport:
    files_examined: int = 0
    files_deleted: int = 0
    runs_purged: int = 0
    failures: int = 0
    retry_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def cleanup_expired_raw_files(db: Session) -> dict:
    now = utc_now()
    report = CleanupReport()
    files = list(
        db.scalars(
            select(UploadedFile).where(
                UploadedFile.retention_expires_at.is_not(None),
                UploadedFile.retention_expires_at <= now,
                UploadedFile.storage_deleted_at.is_(None),
            )
        )
    )
    report.files_examined = len(files)
    storage = get_storage_backend()
    for uploaded_file in files:
        try:
            storage.delete_file(uploaded_file.file_path)
            uploaded_file.storage_deleted_at = now
            uploaded_file.status = "retention_deleted"
            report.files_deleted += 1
        except Exception:
            report.failures += 1
    db.commit()
    return report.to_dict()


def cleanup_expired_reconciliation_data(db: Session) -> dict:
    now = utc_now()
    report = CleanupReport()
    runs = list(
        db.scalars(
            select(ReconciliationRun).where(
                ReconciliationRun.retention_expires_at.is_not(None),
                ReconciliationRun.retention_expires_at <= now,
                ReconciliationRun.data_purged_at.is_(None),
            )
        )
    )
    for run in runs:
        db.execute(
            delete(MatchResult).where(
                MatchResult.reconciliation_run_id == run.id,
                MatchResult.organization_id == run.organization_id,
            )
        )
        run.data_purged_at = now
        run.status = "data_retention_purged"
        report.runs_purged += 1
    db.commit()
    return report.to_dict()
