import csv
from pathlib import Path
from app.services.file_role_service import detect_file_role
from app.services.plan_service import PLAN_DEFINITIONS

def headers(name):
    path=Path(__file__).resolve().parents[3]/name
    with path.open(newline="") as source:return next(csv.reader(source))

def test_supplied_payment_export_role_detection():
    result=detect_file_role(headers("novoriq_payment_export_1000_rows.csv"))
    assert result.detected_role=="payment_export";assert result.confidence>=.9;assert "net_amount" in result.signals

def test_supplied_bank_statement_role_detection():
    result=detect_file_role(headers("novoriq_bank_statement_1000_rows.csv"))
    assert result.detected_role=="bank_statement";assert result.confidence>=.9;assert "deposit_amount" in result.signals

def test_free_beta_limits():
    assert PLAN_DEFINITIONS["free"]["monthly_run_limit"]==10
    assert PLAN_DEFINITIONS["free"]["max_rows_per_file"]==1000
