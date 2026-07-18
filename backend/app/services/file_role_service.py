from dataclasses import dataclass

PAYMENT_SIGNALS = {"net_amount","gross_amount","processor_fee","payout_reference","payout_date","processor","order_id","customer_name","status"}
BANK_SIGNALS = {"deposit_amount","bank_reference","value_date","account_number","transaction_type","currency_code","description"}
VALID_FILE_ROLES = {"payment_export","bank_statement","unknown"}

@dataclass(frozen=True)
class FileRoleDetection:
    detected_role: str
    confidence: float
    signals: list[str]

def detect_file_role(columns: list[str]) -> FileRoleDetection:
    normalized={column.strip().casefold() for column in columns}
    payment=sorted(normalized & PAYMENT_SIGNALS); bank=sorted(normalized & BANK_SIGNALS)
    payment_score=len(payment)/len(PAYMENT_SIGNALS); bank_score=len(bank)/len(BANK_SIGNALS)
    if payment_score >= .3 and payment_score > bank_score: return FileRoleDetection("payment_export",round(min(.99,.55+payment_score*.44),2),payment)
    if bank_score >= .3 and bank_score > payment_score: return FileRoleDetection("bank_statement",round(min(.99,.55+bank_score*.44),2),bank)
    return FileRoleDetection("unknown",round(max(payment_score,bank_score),2),sorted(set(payment+bank)))
