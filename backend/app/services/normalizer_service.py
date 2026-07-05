from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from app.schemas.file import ColumnMapping
from app.utils.money import parse_money


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _get(row: dict[str, Any], column: str | None) -> Any:
    if not column:
        return None
    return row.get(column)


def parse_date(value: Any) -> date | None:
    text = _clean(value)
    if not text:
        return None
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            return pd.to_datetime(text, format=date_format, errors="raise").date()
        except (TypeError, ValueError):
            pass
    try:
        parsed = pd.to_datetime(text, errors="raise")
        return parsed.date()
    except (TypeError, ValueError, OverflowError):
        return None


@dataclass
class RowNormalizationError(Exception):
    reason: str
    field_errors: dict[str, str]


def normalize_row(row: dict[str, Any], mapping: ColumnMapping) -> dict[str, Any]:
    if not any(_clean(value) for value in row.values()):
        raise RowNormalizationError("empty_row", {"row": "The source row is empty."})

    raw_amount = _get(row, mapping.amount)
    if _clean(raw_amount) is None:
        raise RowNormalizationError("missing_required_amount", {"amount": "Amount is required."})
    amount = parse_money(raw_amount)
    if amount is None:
        raise RowNormalizationError("invalid_amount", {"amount": f"Could not parse amount value: {raw_amount}"})
    if abs(amount) > 9999999999.99:
        raise RowNormalizationError("invalid_amount", {"amount": "Amount exceeds the supported size."})

    raw_date = _get(row, mapping.date)
    if _clean(raw_date) is None:
        raise RowNormalizationError("invalid_date", {"date": "Date is required."})
    transaction_date = parse_date(raw_date)
    if transaction_date is None:
        raise RowNormalizationError("invalid_date", {"date": f"Could not parse date value: {raw_date}"})

    reference = _clean(_get(row, mapping.reference))
    if reference is None:
        raise RowNormalizationError(
            "missing_required_reference", {"reference": "Reference is required."}
        )
    if len(reference) > 255:
        raise RowNormalizationError("invalid_reference", {"reference": "Reference exceeds 255 characters."})

    currency = _clean(_get(row, mapping.currency))
    if currency and len(currency) > 10:
        raise RowNormalizationError("invalid_currency", {"currency": "Currency exceeds 10 characters."})
    return {
        "transaction_date": transaction_date,
        "amount": amount,
        "reference": reference,
        "description": _clean(_get(row, mapping.description)),
        "customer_name": _clean(_get(row, mapping.customer_name)),
        "currency": currency.upper() if currency else None,
        "raw_data": row,
    }
