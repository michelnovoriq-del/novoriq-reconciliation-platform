from decimal import Decimal

import pytest
import csv
from pathlib import Path
from fastapi import HTTPException

from app.schemas.file import ColumnMapping
from app.services.file_service import validate_column_mapping
from app.services.normalizer_service import RowNormalizationError, normalize_row
from app.services.parser_service import read_file
from app.utils.money import parse_money


MAPPING = ColumnMapping(date="Paid On", amount="Total", reference="Reference")


def test_normalize_valid_row() -> None:
    result = normalize_row(
        {"Paid On": "2026-06-22", "Total": "USD 1,200.50", "Reference": " INV-1 "},
        MAPPING,
    )
    assert result["amount"] == Decimal("1200.50")
    assert result["transaction_date"].isoformat() == "2026-06-22"
    assert result["reference"] == "INV-1"


@pytest.mark.parametrize(
    ("amount_column", "expected"),
    [("net_amount", "24.37"), ("gross_amount", "24.92")],
)
def test_manual_amount_mapping_is_authoritative(amount_column: str, expected: str) -> None:
    result = normalize_row(
        {
            "payment_date": "2026-07-01",
            "payment_id": "PAY-001",
            "gross_amount": "24.92",
            "net_amount": "24.37",
        },
        ColumnMapping(
            date="payment_date",
            amount=amount_column,
            reference="payment_id",
        ),
    )

    assert str(result["amount"]) == expected


def test_supplied_1000_row_fixtures_use_selected_net_and_deposit_amounts() -> None:
    project_root = Path(__file__).resolve().parents[3]
    with (project_root / "novoriq_payment_export_1000_rows.csv").open(newline="") as source:
        payment = next(csv.DictReader(source))
    with (project_root / "novoriq_bank_statement_1000_rows.csv").open(newline="") as source:
        bank = next(csv.DictReader(source))

    normalized_payment = normalize_row(payment, ColumnMapping(
        date="payout_date", amount="net_amount", reference="payout_reference",
        description="processor", customer_name="customer_name", currency="currency",
    ))
    normalized_bank = normalize_row(bank, ColumnMapping(
        date="value_date", amount="deposit_amount", reference="bank_reference",
        description="description", currency="currency_code",
    ))

    assert normalized_payment["amount"] == normalized_bank["amount"]
    assert normalized_payment["amount"] != parse_money(payment["gross_amount"])


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ({"Paid On": "2026-06-22", "Total": "not-money", "Reference": "A"}, "invalid_amount"),
        ({"Paid On": "impossible", "Total": "10", "Reference": "A"}, "invalid_date"),
        ({"Paid On": "2026-06-22", "Total": "10", "Reference": "  "}, "missing_required_reference"),
        ({"Paid On": "", "Total": "", "Reference": ""}, "empty_row"),
    ],
)
def test_bad_row_has_structured_rejection(row: dict[str, str], reason: str) -> None:
    with pytest.raises(RowNormalizationError) as error:
        normalize_row(row, MAPPING)
    assert error.value.reason == reason
    assert error.value.field_errors


def test_mixed_csv_preserves_empty_row(tmp_path) -> None:
    source = tmp_path / "mixed.csv"
    source.write_text(
        "Paid On,Total,Reference\n"
        "2026-06-22,100.00,OK\n"
        "2026-06-22,bad,BAD-AMOUNT\n"
        "bad-date,100.00,BAD-DATE\n"
        "2026-06-22,100.00,\n"
        ",,\n",
        encoding="utf-8",
    )
    columns, rows = read_file(str(source))
    assert columns == ["Paid On", "Total", "Reference"]
    assert len(rows) == 5
    assert sum(_is_valid(row) for row in rows) == 1


def test_invalid_mapping_returns_diagnostics() -> None:
    mapping = ColumnMapping(date="Missing Date", reference="Reference")
    with pytest.raises(HTTPException) as error:
        validate_column_mapping(mapping, ["Paid On", "Total", "Reference"])
    assert error.value.status_code == 400
    assert error.value.detail["missing_required_fields"] == ["amount"]
    assert error.value.detail["invalid_mapped_columns"] == {
        "date": "Missing Date column was not found in file"
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [("$100.00", "100.00"), ("1,200.50", "1200.50"), ("USD 200.00", "200.00"), ("(45.00)", "-45.00")],
)
def test_supported_money_formats(value: str, expected: str) -> None:
    assert parse_money(value) == Decimal(expected)


def _is_valid(row: dict[str, str]) -> bool:
    try:
        normalize_row(row, MAPPING)
        return True
    except RowNormalizationError:
        return False
