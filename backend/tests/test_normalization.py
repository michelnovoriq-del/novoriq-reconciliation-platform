from decimal import Decimal

import pytest
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
