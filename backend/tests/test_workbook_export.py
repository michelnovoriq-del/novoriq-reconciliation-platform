import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from openpyxl import load_workbook

from app.models import ClientWorkspace, MatchResult, NormalizedRecord, Organization, ReconciliationRun, UploadedFile, User
from app.services.workbook_export_service import build_reconciliation_workbook


def test_accountant_workbook_contains_required_sheets_and_mapping_audit(monkeypatch) -> None:
    organization = Organization(id=uuid.uuid4(), name="Demo Firm")
    user = User(id=uuid.uuid4(), email="owner@example.com", hashed_password="test")
    workspace = ClientWorkspace(id=uuid.uuid4(), organization_id=organization.id, name="Demo Client", slug="demo-client", status="active", created_by_user_id=user.id)
    payment = UploadedFile(id=uuid.uuid4(), organization_id=organization.id, workspace_id=workspace.id, uploaded_by_user_id=user.id, original_filename="novoriq_payment_export_1000_rows.csv", stored_filename="payment.csv", file_path="payment.csv", file_type="csv", status="normalized", row_count=1000, normalization_mapping={"date":"payout_date","amount":"net_amount","reference":"payout_reference"})
    bank = UploadedFile(id=uuid.uuid4(), organization_id=organization.id, workspace_id=workspace.id, uploaded_by_user_id=user.id, original_filename="novoriq_bank_statement_1000_rows.csv", stored_filename="bank.csv", file_path="bank.csv", file_type="csv", status="normalized", row_count=1000, normalization_mapping={"date":"value_date","amount":"deposit_amount","reference":"bank_reference"})
    run = ReconciliationRun(id=uuid.uuid4(), organization_id=organization.id, workspace_id=workspace.id, created_by_user_id=user.id, file_a_id=payment.id, file_b_id=bank.id, status="completed", created_at=datetime.now(timezone.utc)); run.file_a=payment; run.file_b=bank
    left = NormalizedRecord(id=uuid.uuid4(), source_row_number=1, transaction_date=date(2026,7,2), amount=Decimal("695.96"), reference="PAY-1", currency="USD", raw_data={"net_amount":"695.96","gross_amount":"709.64","processor_fee":"13.68"})
    right = NormalizedRecord(id=uuid.uuid4(), source_row_number=1, transaction_date=date(2026,7,4), amount=Decimal("695.96"), reference="PAY-1", currency="USD", raw_data={"account_number":"ACC-1"})
    result = MatchResult(id=uuid.uuid4(), reconciliation_run_id=run.id, organization_id=organization.id, file_a_record_id=left.id, file_b_record_id=right.id, status="approved", suggested_status="confident_match", confidence_score=100, match_reason="Exact net amount and reference.", amount_difference=Decimal("0"), date_difference_days=2); result.file_a_record=left; result.file_b_record=right
    monkeypatch.setattr("app.services.workbook_export_service._load_results", lambda *args, **kwargs: [result])
    db=MagicMock(); db.get.side_effect=lambda model, value: workspace if model is ClientWorkspace else user; db.scalars.return_value=[]

    content=build_reconciliation_workbook(db, run=run, organization=organization)
    workbook=load_workbook(io.BytesIO(content))

    assert workbook.sheetnames == ["Summary","Approved Matches","Exceptions","Unmatched Payment Rows","Unmatched Bank Rows","Mapping Audit","Invalid Rows"]
    mapping_rows=list(workbook["Mapping Audit"].iter_rows(values_only=True))
    amount_column=mapping_rows[0].index("mapped_amount_column")
    assert [row[amount_column] for row in mapping_rows[1:]] == ["net_amount","deposit_amount"]
    assert "match_reason" in [cell.value for cell in workbook["Approved Matches"][1]]
    assert workbook["Invalid Rows"][2][5].value == "No invalid rows found."
