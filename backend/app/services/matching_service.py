import csv
import io
import json
import re
import uuid
from bisect import bisect_left
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from difflib import SequenceMatcher

from fastapi import HTTPException, status
try:
    from rapidfuzz.fuzz import ratio as text_ratio
except ImportError:  # Keeps local startup usable until updated requirements are installed.
    def text_ratio(left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio() * 100
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import MatchResult, NormalizedRecord, Organization, ReconciliationRun, User
from app.services.audit_service import create_audit_log
from app.services.reconciliation_service import get_reconciliation_run
from app.services.upload_safety import neutralize_spreadsheet_formula
from app.services.usage_service import increment_export_usage


MAX_REVIEW_DATE_DIFF_DAYS = 5
MAX_MATCH_DATE_DIFF_DAYS = 3
REFERENCE_STRONG_THRESHOLD = 85
REFERENCE_MODERATE_THRESHOLD = 70
DESCRIPTION_STRONG_THRESHOLD = 80
DESCRIPTION_MODERATE_THRESHOLD = 65
MAX_SMALL_AMOUNT_DIFFERENCE_ABSOLUTE = Decimal("10.00")
MAX_SMALL_AMOUNT_DIFFERENCE_PERCENT = Decimal("0.03")
UNKNOWN_REFERENCE_MARKERS = (
    "UNKNOWN",
    "UNMAPPED",
    "MANUAL",
    "CARD PAYOUT",
    "SHOPIFY PAYOUT",
    "ECOMMERCE SETTLEMENT",
    "BANK TRANSFER",
    "CLIENT PAYMENT",
    "ONLINE PAYMENT",
    "INCOMING PAYMENT",
    "POS SETTLEMENT",
    "LEDGER-ONLY",
    "ACC-ONLY",
    "SHOP-UNKNOWN",
)
EXPORT_COLUMNS = [
    "run_id",
    "created_at",
    "file_a_name",
    "file_b_name",
    "mapping_used_file_a",
    "mapping_used_file_b",
    "status",
    "confidence_score",
    "match_reason",
    "exception_type",
    "file_a_record_id",
    "file_a_original_row_number",
    "amount_difference",
    "date_difference_days",
    "file_a_date",
    "file_a_amount",
    "file_a_reference",
    "file_a_description",
    "file_a_customer_name",
    "file_a_currency",
    "file_a_gross_amount",
    "file_a_processor_fee",
    "file_a_net_amount",
    "file_a_order_id",
    "file_a_processor",
    "file_a_payment_status",
    "file_b_record_id",
    "file_b_original_row_number",
    "file_b_date",
    "file_b_amount",
    "file_b_reference",
    "file_b_description",
    "file_b_customer_name",
    "file_b_currency",
    "file_b_account_number",
    "file_b_transaction_type",
    "file_b_bank_description",
    "approved_by",
    "approved_at",
    "review_status",
]


@dataclass(frozen=True)
class PairScore:
    confidence_score: int
    status: str | None
    amount_difference: Decimal | None
    date_difference_days: int | None
    reference_similarity: int
    description_similarity: int
    reason: str


def _similarity(left: str | None, right: str | None) -> int:
    if not left or not right:
        return 0
    return round(text_ratio(left.strip().casefold(), right.strip().casefold()))


def _normalize_reference(reference: str | None) -> str:
    if not reference:
        return ""
    return re.sub(r"[^A-Z0-9]", "", reference.upper())


def _reference_similarity(left: str | None, right: str | None) -> int:
    normalized_left = _normalize_reference(left)
    normalized_right = _normalize_reference(right)
    if not normalized_left or not normalized_right:
        return 0
    return round(text_ratio(normalized_left, normalized_right))


def _is_unknown_reference(reference: str | None) -> bool:
    if not reference or not reference.strip():
        return True
    normalized = reference.strip().upper()
    return any(marker in normalized for marker in UNKNOWN_REFERENCE_MARKERS)


def analyze_file_compatibility(
    file_a_records: list[NormalizedRecord], file_b_records: list[NormalizedRecord]
) -> dict:
    meaningful_a_references = [
        _normalize_reference(record.reference)
        for record in file_a_records
        if record.reference and not _is_unknown_reference(record.reference)
    ]
    meaningful_b_references = {
        _normalize_reference(record.reference)
        for record in file_b_records
        if record.reference and not _is_unknown_reference(record.reference)
    }
    shared_reference_ratio = (
        sum(reference in meaningful_b_references for reference in meaningful_a_references)
        / len(meaningful_a_references)
        if meaningful_a_references
        else 0.0
    )

    amounts_a = [Decimal(record.amount) for record in file_a_records if record.amount is not None]
    amounts_b = sorted(Decimal(record.amount) for record in file_b_records if record.amount is not None)
    amounts_b_set = set(amounts_b)
    exact_amount_overlap_ratio = (
        sum(amount in amounts_b_set for amount in amounts_a) / len(amounts_a) if amounts_a else 0.0
    )

    def has_close_amount(amount: Decimal) -> bool:
        threshold = max(
            MAX_SMALL_AMOUNT_DIFFERENCE_ABSOLUTE,
            abs(amount) * MAX_SMALL_AMOUNT_DIFFERENCE_PERCENT,
        )
        index = bisect_left(amounts_b, amount)
        nearby = amounts_b[max(0, index - 1) : index + 1]
        return any(abs(amount - candidate) <= threshold for candidate in nearby)

    close_amount_overlap_ratio = (
        sum(has_close_amount(amount) for amount in amounts_a) / len(amounts_a)
        if amounts_a and amounts_b
        else 0.0
    )

    customers_a = [record.customer_name.strip() for record in file_a_records if record.customer_name and record.customer_name.strip()]
    customers_b = list({record.customer_name.strip() for record in file_b_records if record.customer_name and record.customer_name.strip()})
    customer_overlap_ratio = (
        sum(any(_similarity(customer_a, customer_b) >= 85 for customer_b in customers_b) for customer_a in customers_a)
        / len(customers_a)
        if customers_a and customers_b
        else 0.0
    )

    dates_a = [record.transaction_date for record in file_a_records if record.transaction_date]
    dates_b = [record.transaction_date for record in file_b_records if record.transaction_date]
    date_range_overlap = False
    if dates_a and dates_b:
        date_range_overlap = max(min(dates_a), min(dates_b)) <= min(max(dates_a), max(dates_b))
        if not date_range_overlap:
            gap = min(abs((date_a - date_b).days) for date_a in (min(dates_a), max(dates_a)) for date_b in (min(dates_b), max(dates_b)))
            date_range_overlap = gap <= MAX_REVIEW_DATE_DIFF_DAYS

    likely_related = not (
        shared_reference_ratio < 0.02
        and exact_amount_overlap_ratio < 0.02
        and close_amount_overlap_ratio < 0.05
    )
    warnings: list[str] = []
    if not likely_related:
        warnings.append(
            "Files appear weakly related based on low reference and amount overlap. Conservative matching applied."
        )
    if dates_a and dates_b and not date_range_overlap:
        warnings.append("File date ranges do not overlap or fall within five days.")

    return {
        "total_file_a_records": len(file_a_records),
        "total_file_b_records": len(file_b_records),
        "shared_reference_ratio": round(shared_reference_ratio, 4),
        "exact_amount_overlap_ratio": round(exact_amount_overlap_ratio, 4),
        "close_amount_overlap_ratio": round(close_amount_overlap_ratio, 4),
        "customer_overlap_ratio": round(customer_overlap_ratio, 4),
        "date_range_overlap": date_range_overlap,
        "likely_related": likely_related,
        "warnings": warnings,
    }


def score_pair(
    file_a: NormalizedRecord, file_b: NormalizedRecord, *, likely_related: bool = True
) -> PairScore:
    amount_difference = None
    amount_exact = False
    if file_a.amount is not None and file_b.amount is not None:
        amount_difference = abs(Decimal(file_a.amount) - Decimal(file_b.amount))
        amount_exact = amount_difference == Decimal("0.00")

    date_difference = None
    if file_a.transaction_date and file_b.transaction_date:
        date_difference = abs((file_a.transaction_date - file_b.transaction_date).days)

    reference_similarity = _reference_similarity(file_a.reference, file_b.reference)
    description_similarity = max(
        _similarity(file_a.description, file_b.description),
        _similarity(file_a.customer_name, file_b.customer_name),
    )
    order_id = str((file_a.raw_data or {}).get("order_id") or "").strip()
    order_id_match = bool(
        order_id
        and order_id.casefold() in " ".join(
            filter(None, (file_b.reference, file_b.description))
        ).casefold()
    )
    currency_mismatch = bool(
        file_a.currency and file_b.currency and file_a.currency.upper() != file_b.currency.upper()
    )

    small_amount_difference = False
    amount_too_large = False
    if amount_difference is not None and file_a.amount is not None:
        tolerance = max(
            MAX_SMALL_AMOUNT_DIFFERENCE_ABSOLUTE,
            abs(Decimal(file_a.amount)) * MAX_SMALL_AMOUNT_DIFFERENCE_PERCENT,
        )
        small_amount_difference = Decimal("0.00") < amount_difference <= tolerance
        amount_too_large = amount_difference > tolerance

    date_close = date_difference is not None and date_difference <= MAX_MATCH_DATE_DIFF_DAYS
    date_reviewable = date_difference is not None and date_difference <= MAX_REVIEW_DATE_DIFF_DAYS
    reference_strong = reference_similarity >= REFERENCE_STRONG_THRESHOLD
    reference_moderate = reference_similarity >= REFERENCE_MODERATE_THRESHOLD
    description_strong = description_similarity >= 85
    description_moderate = description_similarity >= 80
    file_a_unknown_reference = _is_unknown_reference(file_a.reference)
    file_b_unknown_reference = _is_unknown_reference(file_b.reference)
    unknown_reference = file_a_unknown_reference or file_b_unknown_reference

    score = 40 if amount_exact else 25 if small_amount_difference else 0
    if date_difference == 0:
        score += 20
    elif date_difference is not None and date_difference <= MAX_MATCH_DATE_DIFF_DAYS:
        score += 15
    elif date_difference is not None and date_difference <= MAX_REVIEW_DATE_DIFF_DAYS:
        score += 8
    if reference_similarity >= 90:
        score += 30
    elif reference_strong:
        score += 25
    elif reference_moderate:
        score += 15
    if description_strong:
        score += 10
    elif description_moderate:
        score += 5
    if order_id_match:
        score += 20
    if currency_mismatch:
        score -= 50
    if unknown_reference:
        score -= 25
    if amount_too_large:
        score -= 30
    if reference_similarity < 50:
        score -= 15
    if not likely_related and not amount_exact and not reference_strong:
        score -= 20
    score = max(0, min(score, 100))

    very_small_amount_difference = (
        amount_difference is not None
        and Decimal("0.00") < amount_difference <= Decimal("0.50")
    )
    exact_candidate = (
        (amount_exact or very_small_amount_difference)
        and date_close
        and (reference_strong or description_strong)
    )
    if currency_mismatch:
        exact_candidate = False
    if unknown_reference:
        exact_candidate = (
            amount_exact
            and date_difference is not None
            and date_difference <= 1
            and description_strong
        )

    strong_signals = sum(
        (
            amount_exact,
            small_amount_difference,
            reference_moderate,
            description_strong,
        )
    )
    possible_candidate = date_reviewable and (strong_signals >= 2 or order_id_match)

    rejection_reasons: list[str] = []
    strong_financial_signal = amount_exact or reference_strong or (
        small_amount_difference and reference_strong
    )
    if not strong_financial_signal:
        possible_candidate = False
        rejection_reasons.append("no strong amount or reference evidence")
    if amount_difference is not None and amount_difference > 0 and not reference_moderate:
        possible_candidate = False
        rejection_reasons.append("non-exact amount requires at least 70% reference similarity")
    if amount_too_large and reference_similarity < REFERENCE_STRONG_THRESHOLD:
        possible_candidate = False
        rejection_reasons.append(
            f"amount difference {amount_difference} exceeds threshold and reference similarity "
            f"is only {reference_similarity}%"
        )
    if file_b_unknown_reference and not amount_exact:
        possible_candidate = False
        rejection_reasons.append("File B reference is generic or unknown and amount does not match exactly")
    if (
        reference_similarity < REFERENCE_MODERATE_THRESHOLD
        and description_similarity < DESCRIPTION_MODERATE_THRESHOLD
        and not amount_exact
    ):
        possible_candidate = False
        rejection_reasons.append("text evidence is weak and amount does not match exactly")
    if not date_reviewable:
        possible_candidate = False
        rejection_reasons.append("date difference exceeds 5 days or is unavailable")
    if not likely_related and not (amount_exact or reference_strong):
        possible_candidate = False
        rejection_reasons.append("file compatibility is weak without exact amount or strong reference evidence")

    if currency_mismatch:
        possible_candidate = False
        rejection_reasons.append("currencies do not match")

    late_settlement = (
        amount_exact
        and reference_strong
        and date_difference is not None
        and 5 < date_difference <= 14
        and not currency_mismatch
    )
    amount_variance = (
        small_amount_difference
        and reference_strong
        and date_reviewable
        and not currency_mismatch
    )

    result_status = (
        "late_settlement" if late_settlement
        else "amount_variance" if amount_variance
        else "confident_match" if exact_candidate
        else "possible_match" if possible_candidate
        else None
    )
    if result_status == "confident_match":
        score = max(score, 95)
    elif result_status in {"possible_match", "amount_variance", "late_settlement"}:
        score = min(84, score)
    else:
        score = 0

    amount_text = (
        "Amount matched exactly"
        if amount_exact
        else f"Amount differs by {amount_difference}"
        if amount_difference is not None
        else "Amount unavailable"
    )
    date_text = (
        f"date difference {date_difference} day{'s' if date_difference != 1 else ''}"
        if date_difference is not None
        else "date unavailable"
    )
    evidence = (
        f"{amount_text}, {date_text}, reference similarity {reference_similarity}%, "
        f"description/customer similarity {description_similarity}%"
    )
    if result_status == "amount_variance":
        reason = f"Amount variance: payout reference matches and {date_text}, but the bank amount differs by {amount_difference}."
    elif result_status == "late_settlement":
        reason = f"Late settlement: amount and payout reference match, but the bank deposit arrived {date_difference} days from the payout date."
    elif result_status == "possible_match" and not amount_exact and small_amount_difference:
        reason = f"Possible match: {evidence}. Review as possible fee difference."
    elif result_status == "possible_match":
        reason = f"Possible match: {evidence}. Review supporting evidence."
    elif result_status == "confident_match":
        reason = f"Confident match: {evidence}."
    elif rejection_reasons:
        reason = f"Rejected weak candidate: {'; '.join(rejection_reasons)}."
    else:
        reason = f"Rejected weak candidate: insufficient supporting signals. {evidence}."
    return PairScore(
        confidence_score=min(score, 100),
        status=result_status,
        amount_difference=amount_difference,
        date_difference_days=date_difference,
        reference_similarity=reference_similarity,
        description_similarity=description_similarity,
        reason=reason,
    )


def _records_for_file(db: Session, file_id: uuid.UUID, organization_id: uuid.UUID) -> list[NormalizedRecord]:
    return list(
        db.scalars(
            select(NormalizedRecord)
            .where(
                NormalizedRecord.uploaded_file_id == file_id,
                NormalizedRecord.organization_id == organization_id,
            )
            .order_by(NormalizedRecord.source_row_number)
        )
    )


def select_candidate_pairs(
    records_a: list[NormalizedRecord],
    records_b: list[NormalizedRecord],
    *,
    likely_related: bool = True,
) -> list[tuple[int, int, PairScore]]:
    candidates: list[tuple[int, int, PairScore]] = []
    reference_index: dict[str, set[int]] = {}
    amount_index: dict[Decimal, set[int]] = {}
    order_index: dict[str, set[int]] = {}
    for b_index, record_b in enumerate(records_b):
        normalized_reference = _normalize_reference(record_b.reference)
        if normalized_reference:
            reference_index.setdefault(normalized_reference, set()).add(b_index)
        if record_b.amount is not None:
            amount_index.setdefault(Decimal(record_b.amount), set()).add(b_index)
        text = f"{record_b.reference or ''} {record_b.description or ''}".upper()
        for token in re.findall(r"ORD-[A-Z0-9-]+", text):
            order_index.setdefault(token, set()).add(b_index)
    for a_index, record_a in enumerate(records_a):
        likely_b: set[int] = set()
        normalized_reference = _normalize_reference(record_a.reference)
        if normalized_reference:
            likely_b.update(reference_index.get(normalized_reference, set()))
        if record_a.amount is not None:
            likely_b.update(amount_index.get(Decimal(record_a.amount), set()))
        order_id = str((record_a.raw_data or {}).get("order_id") or "").upper()
        if order_id:
            likely_b.update(order_index.get(order_id, set()))
        # Preserve fuzzy-reference behavior for small files and unusual exports while
        # avoiding a million comparisons for normal 1,000-row reconciliation runs.
        if not likely_b and len(records_a) * len(records_b) <= 10_000:
            likely_b.update(range(len(records_b)))
        for b_index in likely_b:
            record_b = records_b[b_index]
            pair = score_pair(record_a, record_b, likely_related=likely_related)
            if pair.status:
                candidates.append((a_index, b_index, pair))
    candidates.sort(
        key=lambda item: (
            -item[2].confidence_score,
            -(item[2].reference_similarity == 100),
            -(item[2].amount_difference == Decimal("0.00")),
            item[2].date_difference_days
            if item[2].date_difference_days is not None
            else float("inf"),
            item[2].amount_difference
            if item[2].amount_difference is not None
            else Decimal("Infinity"),
            item[0],
            item[1],
        )
    )

    selected: list[tuple[int, int, PairScore]] = []
    used_a: set[int] = set()
    used_b: set[int] = set()
    for a_index, b_index, pair in candidates:
        if a_index in used_a or b_index in used_b:
            continue
        used_a.add(a_index)
        used_b.add(b_index)
        equally_ranked = [
            candidate for candidate in candidates
            if candidate != (a_index, b_index, pair)
            and (candidate[0] == a_index or candidate[1] == b_index)
            and candidate[2].confidence_score == pair.confidence_score
            and candidate[2].amount_difference == pair.amount_difference
            and candidate[2].reference_similarity == pair.reference_similarity
        ]
        if equally_ranked:
            pair = replace(
                pair,
                status="duplicate_candidate",
                confidence_score=min(pair.confidence_score, 84),
                reason=f"Duplicate candidate: {len(equally_ranked) + 1} equally strong records require human review. {pair.reason}",
            )
        selected.append((a_index, b_index, pair))
    return selected


def run_matching(
    db: Session, *, run: ReconciliationRun, user: User, organization: Organization
) -> dict:
    existing = db.scalar(
        select(func.count(MatchResult.id)).where(MatchResult.reconciliation_run_id == run.id)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Matching results already exist for this run.")

    records_a = _records_for_file(db, run.file_a_id, organization.id)
    records_b = _records_for_file(db, run.file_b_id, organization.id)
    if not records_a:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File A has no normalized records.")
    if not records_b:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File B has no normalized records.")

    compatibility = analyze_file_compatibility(records_a, records_b)
    selected_candidates = select_candidate_pairs(
        records_a, records_b, likely_related=compatibility["likely_related"]
    )
    used_a = {item[0] for item in selected_candidates}
    used_b = {item[1] for item in selected_candidates}
    results: list[MatchResult] = []
    for a_index, b_index, pair in selected_candidates:
        results.append(MatchResult(
            organization_id=organization.id,
            reconciliation_run_id=run.id,
            file_a_record_id=records_a[a_index].id,
            file_b_record_id=records_b[b_index].id,
            status=pair.status,
            suggested_status=pair.status,
            confidence_score=pair.confidence_score,
            match_reason=pair.reason,
            amount_difference=pair.amount_difference,
            date_difference_days=pair.date_difference_days,
            reference_similarity=pair.reference_similarity,
            description_similarity=pair.description_similarity,
            duplicate_group_id=uuid.uuid4() if pair.status == "duplicate_candidate" else None,
            duplicate_reason=pair.reason if pair.status == "duplicate_candidate" else None,
        ))
    results.extend(
        MatchResult(
            organization_id=organization.id,
            reconciliation_run_id=run.id,
            file_a_record_id=record.id,
            status="unmatched_file_a",
            suggested_status="unmatched_file_a",
            confidence_score=0,
            match_reason=(
                "No reliable match found. Weak candidates were rejected because amount/reference evidence was insufficient."
                + (" Files appear weakly related; conservative matching was applied." if not compatibility["likely_related"] else "")
            ),
        )
        for index, record in enumerate(records_a) if index not in used_a
    )
    results.extend(
        MatchResult(
            organization_id=organization.id,
            reconciliation_run_id=run.id,
            file_b_record_id=record.id,
            status="unmatched_file_b",
            suggested_status="unmatched_file_b",
            confidence_score=0,
            match_reason=(
                "No reliable match found. Weak candidates were rejected because amount/reference evidence was insufficient."
                + (" Files appear weakly related; conservative matching was applied." if not compatibility["likely_related"] else "")
            ),
        )
        for index, record in enumerate(records_b) if index not in used_b
    )
    db.add_all(results)
    run.status = "completed"
    create_audit_log(
        db,
        organization_id=organization.id,
        user_id=user.id,
        action="reconciliation_matching_completed",
        entity_type="reconciliation_run",
        entity_id=run.id,
        metadata={"result_count": len(results), "file_compatibility": compatibility},
    )
    db.commit()
    return build_results_response(db, run=run, organization=organization)


def _load_results(db: Session, run_id: uuid.UUID, organization_id: uuid.UUID) -> list[MatchResult]:
    return list(db.scalars(
        select(MatchResult)
        .options(selectinload(MatchResult.file_a_record), selectinload(MatchResult.file_b_record))
        .where(
            MatchResult.reconciliation_run_id == run_id,
            MatchResult.organization_id == organization_id,
        )
        .order_by(MatchResult.created_at, MatchResult.id)
    ))


def build_results_response(db: Session, *, run: ReconciliationRun, organization: Organization) -> dict:
    results = _load_results(db, run.id, organization.id)
    green = [item for item in results if item.status in {"confident_match", "approved"}]
    yellow = [item for item in results if item.status in {"possible_match", "amount_variance", "late_settlement", "duplicate_candidate", "manual_review_required"}]
    red = [item for item in results if item.status in {"unmatched_file_a", "unmatched_file_b", "reviewed_unmatched", "rejected"}]
    return {
        "run_id": run.id,
        "status": run.status,
        "green_matches": green,
        "yellow_possible_matches": yellow,
        "red_unmatched": red,
        "summary": {
            "total_matches": len(results),
            "green_count": len(green),
            "yellow_count": len(yellow),
            "red_count": len(red),
            "approved_count": sum(item.status == "approved" for item in results),
            "rejected_count": sum(item.status == "rejected" for item in results),
            "confident_count": sum(item.status == "confident_match" for item in results),
            "possible_count": sum(item.status == "possible_match" for item in results),
            "amount_variance_count": sum(item.status == "amount_variance" for item in results),
            "late_settlement_count": sum(item.status == "late_settlement" for item in results),
            "duplicate_candidate_count": sum(item.status == "duplicate_candidate" for item in results),
            "unmatched_file_a_count": sum(item.suggested_status == "unmatched_file_a" for item in results),
            "unmatched_file_b_count": sum(item.suggested_status == "unmatched_file_b" for item in results),
        },
    }


def get_results(db: Session, *, run_id: uuid.UUID, organization: Organization) -> dict:
    run = get_reconciliation_run(db, run_id=run_id, organization=organization)
    return build_results_response(db, run=run, organization=organization)


def review_match(
    db: Session, *, match_id: uuid.UUID, decision: str, user: User, organization: Organization
) -> MatchResult:
    result = db.scalar(select(MatchResult).where(
        MatchResult.id == match_id, MatchResult.organization_id == organization.id
    ))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match result not found.")
    result.status = decision
    result.reviewed_by_user_id = user.id
    result.reviewed_at = datetime.now(timezone.utc)
    run = get_reconciliation_run(db, run_id=result.reconciliation_run_id, organization=organization)
    create_audit_log(
        db,
        organization_id=organization.id,
        workspace_id=run.workspace_id,
        user_id=user.id,
        action=f"match_result_{decision}",
        entity_type="match_result",
        entity_id=result.id,
    )
    db.commit()
    db.refresh(result)
    return result


def mark_unmatched_reviewed(db: Session, *, match_id: uuid.UUID, notes: str | None, user: User, organization: Organization) -> MatchResult:
    result = db.scalar(select(MatchResult).where(MatchResult.id == match_id, MatchResult.organization_id == organization.id))
    if not result:
        raise HTTPException(status_code=404, detail="Match result not found.")
    if result.suggested_status not in {"unmatched_file_a", "unmatched_file_b"}:
        raise HTTPException(status_code=400, detail="Only unmatched rows can be marked reviewed.")
    result.status = "reviewed_unmatched"; result.review_notes = notes; result.reviewed_by_user_id = user.id; result.reviewed_at = datetime.now(timezone.utc)
    run = get_reconciliation_run(db, run_id=result.reconciliation_run_id, organization=organization)
    create_audit_log(db, organization_id=organization.id, workspace_id=run.workspace_id, user_id=user.id, action="unmatched_result_reviewed", entity_type="match_result", entity_id=result.id, metadata={"notes": notes} if notes else None)
    db.commit(); db.refresh(result); return result


def undo_review(db: Session, *, match_id: uuid.UUID, user: User, organization: Organization) -> MatchResult:
    result = db.scalar(select(MatchResult).where(MatchResult.id == match_id, MatchResult.organization_id == organization.id))
    if not result:
        raise HTTPException(status_code=404, detail="Match result not found.")
    if result.status == result.suggested_status:
        raise HTTPException(status_code=400, detail="This result has no review to undo.")
    previous = result.status; result.status = result.suggested_status; result.reviewed_by_user_id = None; result.reviewed_at = None; result.review_notes = None
    run = get_reconciliation_run(db, run_id=result.reconciliation_run_id, organization=organization)
    create_audit_log(db, organization_id=organization.id, workspace_id=run.workspace_id, user_id=user.id, action="match_result_review_undone", entity_type="match_result", entity_id=result.id, metadata={"previous_status": previous, "restored_status": result.suggested_status})
    db.commit(); db.refresh(result); return result


def export_results(
    db: Session, *, run_id: uuid.UUID, user: User, organization: Organization
) -> str:
    run = get_reconciliation_run(db, run_id=run_id, organization=organization)
    results = _load_results(db, run.id, organization.id)
    if not results:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run matching before exporting results.")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for result in results:
        row = {
            "run_id": run.id,
            "created_at": result.created_at,
            "file_a_name": run.file_a.original_filename,
            "file_b_name": run.file_b.original_filename,
            "mapping_used_file_a": json.dumps(run.file_a.normalization_mapping or {}, sort_keys=True),
            "mapping_used_file_b": json.dumps(run.file_b.normalization_mapping or {}, sort_keys=True),
            "status": result.status,
            "confidence_score": result.confidence_score,
            "match_reason": result.match_reason,
            "exception_type": result.status if result.status in {"amount_variance", "late_settlement", "duplicate_candidate", "manual_review_required"} else "",
            "file_a_record_id": result.file_a_record_id,
            "file_a_original_row_number": result.file_a_record.source_row_number if result.file_a_record else None,
            "file_b_record_id": result.file_b_record_id,
            "file_b_original_row_number": result.file_b_record.source_row_number if result.file_b_record else None,
            "amount_difference": result.amount_difference,
            "date_difference_days": result.date_difference_days,
            "approved_by": result.reviewed_by_user_id,
            "approved_at": result.reviewed_at if result.status == "approved" else None,
            "review_status": result.status if result.status in {"approved", "rejected"} else "pending",
        }
        for prefix, record in (("file_a", result.file_a_record), ("file_b", result.file_b_record)):
            row.update({
                f"{prefix}_date": record.transaction_date if record else None,
                f"{prefix}_amount": record.amount if record else None,
                f"{prefix}_reference": record.reference if record else None,
                f"{prefix}_description": record.description if record else None,
                f"{prefix}_customer_name": record.customer_name if record else None,
                f"{prefix}_currency": record.currency if record else None,
            })
        raw_a = result.file_a_record.raw_data if result.file_a_record else {}
        raw_b = result.file_b_record.raw_data if result.file_b_record else {}
        row.update({
            "file_a_gross_amount": raw_a.get("gross_amount"),
            "file_a_processor_fee": raw_a.get("processor_fee"),
            "file_a_net_amount": raw_a.get("net_amount"),
            "file_a_order_id": raw_a.get("order_id"),
            "file_a_processor": raw_a.get("processor"),
            "file_a_payment_status": raw_a.get("status"),
            "file_b_account_number": raw_b.get("account_number"),
            "file_b_transaction_type": raw_b.get("transaction_type"),
            "file_b_bank_description": raw_b.get("description"),
        })
        writer.writerow({key: neutralize_spreadsheet_formula(value) for key, value in row.items()})
    create_audit_log(
        db, organization_id=organization.id, workspace_id=run.workspace_id, user_id=user.id, action="reconciliation_exported",
        entity_type="reconciliation_run", entity_id=run.id,
    )
    increment_export_usage(db, organization.id)
    db.commit()
    return output.getvalue()
