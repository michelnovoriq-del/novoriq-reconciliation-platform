import os
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models import NormalizedRecord, Organization, RejectedRecord, UploadedFile, User
from app.schemas.file import ColumnMapping
from app.services.file_service import list_rejected_records, normalize_uploaded_file


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def test_mixed_rows_are_stored_independently(tmp_path) -> None:
    engine = create_engine(TEST_DATABASE_URL)
    source = tmp_path / "mixed.csv"
    source.write_text(
        (Path(__file__).parent / "data" / "sample_normalization_mixed.csv").read_text(),
        encoding="utf-8",
    )
    with Session(engine) as db:
        organization = Organization(name=f"Normalization test {uuid.uuid4()}")
        user = User(email=f"normalize-{uuid.uuid4()}@example.com", hashed_password="test")
        db.add_all([organization, user])
        db.flush()
        uploaded_file = UploadedFile(
            organization_id=organization.id,
            uploaded_by_user_id=user.id,
            original_filename="mixed.csv",
            stored_filename="mixed.csv",
            file_path=str(source),
            file_type="csv",
            status="uploaded",
        )
        db.add(uploaded_file)
        db.commit()

        result = normalize_uploaded_file(
            db,
            file_id=uploaded_file.id,
            mapping=ColumnMapping(
                date="Paid On", amount="Total Received", reference="Transaction ID"
            ),
            user=user,
            organization=organization,
        )
        assert result["total_rows"] == 5
        assert result["valid_rows"] == 1
        assert result["rejected_rows"] == 4
        assert result["status"] == "normalized_with_rejections"
        assert db.scalar(
            select(func.count()).select_from(NormalizedRecord).where(
                NormalizedRecord.uploaded_file_id == uploaded_file.id
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(RejectedRecord).where(
                RejectedRecord.uploaded_file_id == uploaded_file.id
            )
        ) == 4
        rejected = list_rejected_records(db, file_id=uploaded_file.id, organization=organization)
        assert rejected.total_rejected == 4

        other_organization = Organization(name=f"Other {uuid.uuid4()}")
        db.add(other_organization)
        db.commit()
        with pytest.raises(HTTPException) as error:
            list_rejected_records(db, file_id=uploaded_file.id, organization=other_organization)
        assert error.value.status_code == 403

        all_bad_source = tmp_path / "all-bad.csv"
        all_bad_source.write_text(
            "Paid On,Total Received,Transaction ID\n"
            "bad-date,not-money,\n"
            ",,\n",
            encoding="utf-8",
        )
        all_bad_file = UploadedFile(
            organization_id=organization.id,
            uploaded_by_user_id=user.id,
            original_filename="all-bad.csv",
            stored_filename="all-bad.csv",
            file_path=str(all_bad_source),
            file_type="csv",
            status="uploaded",
        )
        db.add(all_bad_file)
        db.commit()
        with pytest.raises(HTTPException) as all_bad_error:
            normalize_uploaded_file(
                db,
                file_id=all_bad_file.id,
                mapping=ColumnMapping(
                    date="Paid On", amount="Total Received", reference="Transaction ID"
                ),
                user=user,
                organization=organization,
            )
        assert all_bad_error.value.status_code == 400
        assert all_bad_error.value.detail["status"] == "failed"
        assert all_bad_error.value.detail["valid_rows"] == 0
        assert all_bad_error.value.detail["rejected_rows"] == 2
        db.refresh(all_bad_file)
        assert all_bad_file.status == "failed_normalization"


def _normalize_payment_amount(tmp_path, amount_column: str):
    engine = create_engine(TEST_DATABASE_URL)
    source = tmp_path / f"payments-{amount_column}.csv"
    source.write_text(
        "payment_date,payment_id,gross_amount,net_amount\n"
        "2026-07-01,PAY-001,24.92,24.37\n",
        encoding="utf-8",
    )
    with Session(engine) as db:
        organization = Organization(name=f"Mapping test {uuid.uuid4()}")
        user = User(email=f"mapping-{uuid.uuid4()}@example.com", hashed_password="test")
        db.add_all([organization, user])
        db.flush()
        uploaded_file = UploadedFile(
            organization_id=organization.id,
            uploaded_by_user_id=user.id,
            original_filename=source.name,
            stored_filename=source.name,
            file_path=str(source),
            file_type="csv",
            status="uploaded",
        )
        db.add(uploaded_file)
        db.commit()

        normalize_uploaded_file(
            db,
            file_id=uploaded_file.id,
            mapping=ColumnMapping(
                date="payment_date",
                amount=amount_column,
                reference="payment_id",
            ),
            user=user,
            organization=organization,
        )
        return db.scalar(
            select(NormalizedRecord)
            .where(NormalizedRecord.uploaded_file_id == uploaded_file.id)
            .order_by(NormalizedRecord.source_row_number)
        ).amount


def test_manual_net_amount_mapping_is_persisted(tmp_path) -> None:
    assert str(_normalize_payment_amount(tmp_path, "net_amount")) == "24.37"


def test_manual_gross_amount_mapping_is_persisted(tmp_path) -> None:
    assert str(_normalize_payment_amount(tmp_path, "gross_amount")) == "24.92"
