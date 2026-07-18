from datetime import date
from decimal import Decimal

from app.models import NormalizedRecord
from app.services.matching_service import (
    EXPORT_COLUMNS,
    analyze_file_compatibility,
    score_pair,
    select_candidate_pairs,
)


def record(
    *,
    amount: str,
    transaction_date: date,
    reference: str,
    customer: str = "",
    description: str = "",
) -> NormalizedRecord:
    return NormalizedRecord(
        amount=Decimal(amount),
        transaction_date=transaction_date,
        reference=reference,
        customer_name=customer,
        description=description,
        source_row_number=1,
        raw_data={},
    )


def test_exact_amount_near_date_and_reference_is_matched() -> None:
    left = record(amount="100.00", transaction_date=date(2026, 6, 1), reference="INV-001", customer="Acme Ltd")
    right = record(amount="100.00", transaction_date=date(2026, 6, 2), reference="INV-001", customer="Acme Ltd")

    result = score_pair(left, right)

    assert result.status == "confident_match"
    assert 95 <= result.confidence_score <= 100
    assert result.amount_difference == Decimal("0.00")
    assert result.date_difference_days == 1
    assert "reference similarity 100%" in result.reason


def test_small_fee_difference_is_amount_variance() -> None:
    left = record(amount="75.50", transaction_date=date(2026, 6, 5), reference="INV-003", customer="Delta Studio")
    right = record(amount="72.50", transaction_date=date(2026, 6, 5), reference="INV-003", customer="Delta Studio")

    result = score_pair(left, right)

    assert result.status == "amount_variance"
    assert 50 <= result.confidence_score <= 84
    assert result.amount_difference == Decimal("3.00")
    assert "Amount variance" in result.reason


def test_large_amount_difference_and_weak_reference_is_unmatched() -> None:
    left = record(amount="1000.00", transaction_date=date(2026, 6, 10), reference="INV-00768")
    right = record(amount="918.37", transaction_date=date(2026, 6, 12), reference="UNKNOWN-0043")

    result = score_pair(left, right)

    assert result.status is None
    assert result.confidence_score == 0
    assert result.amount_difference == Decimal("81.63")
    assert result.reference_similarity < 50
    assert "Rejected weak candidate" in result.reason


def test_unknown_reference_with_non_exact_amount_is_unmatched() -> None:
    left = record(
        amount="100.00",
        transaction_date=date(2026, 6, 10),
        reference="INV-0043",
        customer="Acme",
    )
    right = record(
        amount="97.00",
        transaction_date=date(2026, 6, 10),
        reference="UNKNOWN-0043",
        customer="Acme",
    )

    result = score_pair(left, right)

    assert result.status is None
    assert "generic or unknown" in result.reason


def test_moderate_reference_exact_amount_and_close_date_is_possible() -> None:
    left = record(amount="250.00", transaction_date=date(2026, 6, 10), reference="INV-12345")
    right = record(amount="250.00", transaction_date=date(2026, 6, 12), reference="INV-123XX")

    result = score_pair(left, right)

    assert result.reference_similarity >= 70
    assert result.status == "possible_match"
    assert "Review supporting evidence" in result.reason


def test_date_beyond_review_window_is_unmatched() -> None:
    left = record(amount="250.00", transaction_date=date(2026, 6, 1), reference="INV-12345")
    right = record(amount="250.00", transaction_date=date(2026, 6, 7), reference="INV-123XX")

    result = score_pair(left, right)

    assert result.status is None
    assert "date difference exceeds 5 days" in result.reason


def test_one_file_b_record_is_assigned_once_to_best_candidate() -> None:
    weaker = record(
        amount="100.00", transaction_date=date(2026, 6, 1), reference="INV-123XX"
    )
    stronger = record(
        amount="100.00", transaction_date=date(2026, 6, 1), reference="INV-12345"
    )
    bank_record = record(
        amount="100.00", transaction_date=date(2026, 6, 2), reference="INV-12345"
    )

    selected = select_candidate_pairs([weaker, stronger], [bank_record])

    assert len(selected) == 1
    assert selected[0][0] == 1
    assert selected[0][1] == 0
    assert selected[0][2].status == "confident_match"


def test_customer_similarity_alone_does_not_create_possible_match() -> None:
    left = record(
        amount="100.00",
        transaction_date=date(2026, 6, 10),
        reference="INVOICE-100",
        customer="Shared Customer",
    )
    right = record(
        amount="97.00",
        transaction_date=date(2026, 6, 10),
        reference="PAYMENT-900",
        customer="Shared Customer",
    )

    result = score_pair(left, right)

    assert result.status is None
    assert "reference" in result.reason


def test_generic_card_payout_with_non_exact_amount_is_unmatched() -> None:
    left = record(
        amount="100.00",
        transaction_date=date(2026, 6, 10),
        reference="INVOICE-100",
        customer="Acme",
    )
    right = record(
        amount="97.00",
        transaction_date=date(2026, 6, 10),
        reference="Card payout",
        customer="Acme",
    )

    result = score_pair(left, right)

    assert result.status is None
    assert "generic or unknown" in result.reason


def test_unrelated_files_apply_strict_mode_and_stay_unmatched() -> None:
    records_a = [
        record(
            amount=str(1000 + index * 100),
            transaction_date=date(2026, 6, index + 1),
            reference=f"INV-{index:03d}",
            customer="Shared Customer",
        )
        for index in range(5)
    ]
    records_b = [
        record(
            amount=str(20 + index * 7),
            transaction_date=date(2026, 6, index + 1),
            reference=f"BANK-{index + 500:03d}",
            customer="Shared Customer",
        )
        for index in range(5)
    ]

    compatibility = analyze_file_compatibility(records_a, records_b)
    selected = select_candidate_pairs(
        records_a, records_b, likely_related=compatibility["likely_related"]
    )

    assert compatibility["likely_related"] is False
    assert compatibility["shared_reference_ratio"] == 0
    assert compatibility["exact_amount_overlap_ratio"] == 0
    assert compatibility["close_amount_overlap_ratio"] == 0
    assert compatibility["customer_overlap_ratio"] == 1
    assert selected == []


def test_weak_file_compatibility_requires_exact_amount_or_strong_reference() -> None:
    left = record(
        amount="100.00",
        transaction_date=date(2026, 6, 10),
        reference="INVOICE-100",
        description="Order settlement",
    )
    right = record(
        amount="97.00",
        transaction_date=date(2026, 6, 10),
        reference="INVOICE-XYZ",
        description="Order settlement",
    )

    result = score_pair(left, right, likely_related=False)

    assert result.reference_similarity < 85
    assert result.status is None
    assert "file compatibility is weak" in result.reason


def test_export_columns_include_accountant_review_evidence() -> None:
    assert {"run_id", "confidence_score", "match_reason", "exception_type",
            "amount_difference", "date_difference_days", "file_a_net_amount",
            "file_a_processor_fee", "file_b_bank_description", "review_status"} <= set(EXPORT_COLUMNS)


def test_equally_strong_candidates_are_flagged_as_duplicates() -> None:
    payment = record(amount="100.00", transaction_date=date(2026, 6, 1), reference="PAY-1")
    bank_a = record(amount="100.00", transaction_date=date(2026, 6, 1), reference="PAY-1")
    bank_b = record(amount="100.00", transaction_date=date(2026, 6, 1), reference="PAY-1")

    selected = select_candidate_pairs([payment], [bank_a, bank_b])

    assert len(selected) == 1
    assert selected[0][2].status == "duplicate_candidate"
    assert "human review" in selected[0][2].reason
