import io
import json
import uuid
from datetime import datetime, timezone
from typing import Iterable

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClientWorkspace, Organization, ReconciliationRun, RejectedRecord, User
from app.services.matching_service import _load_results

HEADER_FILL = PatternFill("solid", fgColor="123B5D")
HEADER_FONT = Font(color="FFFFFF", bold=True)

def _value(value):
    if value is None: return ""
    if isinstance(value, (dict, list)): return json.dumps(value, sort_keys=True, default=str)
    if isinstance(value, uuid.UUID): return str(value)
    if isinstance(value, datetime) and value.tzinfo: return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value

def _table(sheet, headers: list[str], rows: Iterable[list]) -> None:
    sheet.append(headers)
    for cell in sheet[1]: cell.fill = HEADER_FILL; cell.font = HEADER_FONT
    sheet.freeze_panes = "A2"; sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"
    for row in rows: sheet.append([_value(value) for value in row])
    for index, header in enumerate(headers, 1): sheet.column_dimensions[get_column_letter(index)].width = min(max(len(header) + 2, 14), 34)

def _recommended(status: str) -> str:
    return {
        "amount_variance": "Review processor fee or adjustment.", "late_settlement": "Check whether this bank deposit settled late.",
        "duplicate_candidate": "Confirm the correct source and bank rows before approval.", "possible_match": "Compare both source rows before approval.",
        "manual_review_required": "Review the supporting source evidence.", "rejected": "Review the rejection reason and source rows.",
    }.get(status, "Review the source evidence before resolving this exception.")

def build_reconciliation_workbook(db: Session, *, run: ReconciliationRun, organization: Organization) -> bytes:
    results = _load_results(db, run.id, organization.id)
    workspace = db.get(ClientWorkspace, run.workspace_id) if run.workspace_id else None
    creator = db.get(User, run.created_by_user_id)
    rejected = list(db.scalars(select(RejectedRecord).where(RejectedRecord.organization_id == organization.id, RejectedRecord.uploaded_file_id.in_([run.file_a_id, run.file_b_id]))))
    counts = {status: sum(item.status == status for item in results) for status in {item.status for item in results}}
    workbook = Workbook(); summary = workbook.active; summary.title = "Summary"
    summary["A1"] = "Novoriq Reconciliation Summary"; summary["A1"].font = Font(size=18, bold=True, color="123B5D")
    summary_rows = [
        ("Client / Workspace", workspace.name if workspace else "Unassigned"), ("Organization", organization.name), ("Run ID", str(run.id)),
        ("Created At", run.created_at), ("Created By", creator.email if creator else str(run.created_by_user_id)), ("Review Status", "reviewed" if any(x.reviewed_at for x in results) else "pending_review"),
        ("Payment File", run.file_a.original_filename), ("Bank File", run.file_b.original_filename),
        ("Payment Mapping Used", run.file_a.normalization_mapping or {}), ("Bank Mapping Used", run.file_b.normalization_mapping or {}),
        ("Total Payment Rows", run.file_a.row_count or 0), ("Total Bank Rows", run.file_b.row_count or 0), ("Total Rows Processed", (run.file_a.row_count or 0) + (run.file_b.row_count or 0)),
        ("Confident Matches", counts.get("confident_match", 0)), ("Approved Matches", counts.get("approved", 0)), ("Possible Matches", counts.get("possible_match", 0)),
        ("Amount Variances", counts.get("amount_variance", 0)), ("Late Settlements", counts.get("late_settlement", 0)), ("Duplicate Candidates", counts.get("duplicate_candidate", 0)),
        ("Unmatched Payment Rows", counts.get("unmatched_file_a", 0)), ("Unmatched Bank Rows", counts.get("unmatched_file_b", 0)), ("Invalid Rows", len(rejected)),
        ("Manual Review Required", counts.get("manual_review_required", 0)), ("Estimated Time Saved", f"{round((run.file_a.row_count or 0) / 100 * 20)} minutes (estimate)"),
        ("Export Generated At", datetime.now(timezone.utc)),
    ]
    for row_index, (label, value) in enumerate(summary_rows, 3): summary.cell(row_index, 1, label).font = Font(bold=True); summary.cell(row_index, 2, _value(value))
    summary.cell(len(summary_rows) + 5, 1, "Novoriq suggests matches using deterministic rules. Human approval remains the source of truth.")
    summary.column_dimensions["A"].width = 30; summary.column_dimensions["B"].width = 80

    match_headers = ["match_id","status","review_status","confidence_score","match_reason","approved_by","approved_at","payment_row_number","payment_date","payment_reference","payment_order_id","payment_customer_name","payment_processor","payment_gross_amount","payment_processor_fee","payment_net_amount","payment_amount_used","payment_currency","payment_status","bank_row_number","bank_date","bank_reference","bank_description","bank_amount","bank_currency","bank_account_number","bank_transaction_type","amount_difference","date_difference_days"]
    def match_row(item):
        a=item.file_a_record; b=item.file_b_record; ar=a.raw_data if a else {}; br=b.raw_data if b else {}
        return [item.id,item.status,"approved" if item.status=="approved" else "pending_review",item.confidence_score,item.match_reason,item.reviewed_by_user_id,item.reviewed_at,a.source_row_number if a else None,a.transaction_date if a else None,a.reference if a else None,ar.get("order_id"),a.customer_name if a else None,ar.get("processor"),ar.get("gross_amount"),ar.get("processor_fee"),ar.get("net_amount"),a.amount if a else None,a.currency if a else None,ar.get("status"),b.source_row_number if b else None,b.transaction_date if b else None,b.reference if b else None,b.description if b else None,b.amount if b else None,b.currency if b else None,br.get("account_number"),br.get("transaction_type"),item.amount_difference,item.date_difference_days]
    approved = workbook.create_sheet("Approved Matches"); _table(approved, match_headers, (match_row(x) for x in results if x.status == "approved"))

    exceptions = workbook.create_sheet("Exceptions"); exception_headers=["exception_id","exception_type","risk_level","status","review_status","confidence_score","match_reason","recommended_action","payment_row_number","payment_date","payment_reference","payment_order_id","payment_amount","payment_currency","payment_status","bank_row_number","bank_date","bank_reference","bank_description","bank_amount","bank_currency","amount_difference","date_difference_days","review_notes","reviewed_by","reviewed_at"]
    exception_statuses={"possible_match","amount_variance","late_settlement","duplicate_candidate","manual_review_required","currency_mismatch","unclear_reference","rejected"}
    def exception_row(x):
        a=x.file_a_record;b=x.file_b_record;ar=a.raw_data if a else {}
        return [x.id,x.suggested_status,"high" if x.suggested_status in {"duplicate_candidate","currency_mismatch"} else "medium",x.status,"reviewed" if x.reviewed_at else "pending_review",x.confidence_score,x.match_reason,_recommended(x.suggested_status),a.source_row_number if a else None,a.transaction_date if a else None,a.reference if a else None,ar.get("order_id"),a.amount if a else None,a.currency if a else None,ar.get("status"),b.source_row_number if b else None,b.transaction_date if b else None,b.reference if b else None,b.description if b else None,b.amount if b else None,b.currency if b else None,x.amount_difference,x.date_difference_days,x.review_notes,x.reviewed_by_user_id,x.reviewed_at]
    _table(exceptions, exception_headers, (exception_row(x) for x in results if x.suggested_status in exception_statuses))

    unmatched_headers=["record_id","row_number","date","reference","description","amount_used","currency","unmatched_reason","recommended_action","review_status","reviewed_by","reviewed_at","review_notes"]
    for title,status,side,action in (("Unmatched Payment Rows","unmatched_file_a","file_a_record","Check whether the bank statement is missing a deposit or the payout settled outside tolerance."),("Unmatched Bank Rows","unmatched_file_b","file_b_record","Check whether this deposit belongs to another processor or a missing payment export row.")):
        sheet=workbook.create_sheet(title)
        def rows(status=status,side=side,action=action):
            for x in results:
                if x.suggested_status != status: continue
                record=getattr(x,side); yield [record.id,record.source_row_number,record.transaction_date,record.reference,record.description,record.amount,record.currency,x.match_reason,action,"reviewed_unmatched" if x.status=="reviewed_unmatched" else "pending_review",x.reviewed_by_user_id,x.reviewed_at,x.review_notes]
        _table(sheet,unmatched_headers,rows())

    mapping=workbook.create_sheet("Mapping Audit"); mapping_headers=["file_id","file_name","file_type","uploaded_at","mapped_date_column","mapped_amount_column","mapped_reference_column","mapped_description_column","mapped_currency_column","mapped_customer_column","normalized_row_count","mapping_source","mapping_json"]
    _table(mapping,mapping_headers,([f.id,f.original_filename,f.file_type,f.created_at,(f.normalization_mapping or {}).get("date"),(f.normalization_mapping or {}).get("amount"),(f.normalization_mapping or {}).get("reference"),(f.normalization_mapping or {}).get("description"),(f.normalization_mapping or {}).get("currency"),(f.normalization_mapping or {}).get("customer_name"),f.row_count,"manual_or_suggested",f.normalization_mapping or {}] for f in (run.file_a,run.file_b)))
    invalid=workbook.create_sheet("Invalid Rows"); invalid_headers=["file_id","file_name","row_number","field_name","raw_value","error_reason","recommended_fix","created_at"]
    file_names={run.file_a_id:run.file_a.original_filename,run.file_b_id:run.file_b.original_filename}; invalid_rows=[]
    for item in rejected:
        errors=item.field_errors or {"row":item.rejection_reason}
        for field,reason in errors.items(): invalid_rows.append([item.uploaded_file_id,file_names.get(item.uploaded_file_id,""),item.source_row_number,field,(item.raw_data or {}).get(field),reason,"Correct the source value and normalize the file again.",item.created_at])
    _table(invalid,invalid_headers,invalid_rows or [["","","","","","No invalid rows found.","",""]])
    output=io.BytesIO(); workbook.save(output); return output.getvalue()
