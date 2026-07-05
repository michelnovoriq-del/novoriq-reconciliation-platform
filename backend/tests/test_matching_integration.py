import csv
import io
import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import NormalizedRecord, Organization, ReconciliationRun, UploadedFile, User
from app.services.matching_service import EXPORT_COLUMNS, export_results, get_results, run_matching


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def test_strict_matching_persists_red_rows_and_exports_csv() -> None:
    engine = create_engine(TEST_DATABASE_URL)
    unique = uuid.uuid4()
    with Session(engine) as db:
        organization = Organization(name=f"Matching integration {unique}")
        user = User(email=f"matching-{unique}@example.com", hashed_password="test")
        db.add_all([organization, user])
        db.flush()
        file_a = _file(organization.id, user.id, f"a-{unique}.csv")
        file_b = _file(organization.id, user.id, f"b-{unique}.csv")
        db.add_all([file_a, file_b])
        db.flush()
        db.add_all(
            [
                _record(organization.id, file_a.id, 1, "100.00", date(2026, 6, 1), "INV-001"),
                _record(organization.id, file_a.id, 2, "1000.00", date(2026, 6, 10), "INV-00768"),
                _record(organization.id, file_b.id, 1, "100.00", date(2026, 6, 2), "INV-001"),
                _record(organization.id, file_b.id, 2, "918.37", date(2026, 6, 12), "UNKNOWN-0043"),
            ]
        )
        run = ReconciliationRun(
            organization_id=organization.id,
            created_by_user_id=user.id,
            file_a_id=file_a.id,
            file_b_id=file_b.id,
            status="created",
        )
        db.add(run)
        db.commit()

        response = run_matching(db, run=run, user=user, organization=organization)
        assert response["summary"]["green_count"] == 1
        assert response["summary"]["yellow_count"] == 0
        assert response["summary"]["red_count"] == 2

        exported = list(
            csv.DictReader(
                io.StringIO(
                    export_results(db, run_id=run.id, user=user, organization=organization)
                )
            )
        )
        assert list(exported[0]) == EXPORT_COLUMNS
        assert {row["result_status"] for row in exported} == {
            "matched",
            "unmatched_file_a",
            "unmatched_file_b",
        }

        other_organization = Organization(name=f"Other matching org {unique}")
        db.add(other_organization)
        db.commit()
        with pytest.raises(HTTPException) as isolation_error:
            get_results(db, run_id=run.id, organization=other_organization)
        assert isolation_error.value.status_code == 404


def _file(organization_id, user_id, filename: str) -> UploadedFile:
    return UploadedFile(
        organization_id=organization_id,
        uploaded_by_user_id=user_id,
        original_filename=filename,
        stored_filename=filename,
        file_path=filename,
        file_type="csv",
        status="normalized",
    )


def _record(
    organization_id,
    uploaded_file_id,
    row_number: int,
    amount: str,
    transaction_date: date,
    reference: str,
) -> NormalizedRecord:
    return NormalizedRecord(
        organization_id=organization_id,
        uploaded_file_id=uploaded_file_id,
        source_row_number=row_number,
        amount=Decimal(amount),
        transaction_date=transaction_date,
        reference=reference,
        raw_data={},
    )
