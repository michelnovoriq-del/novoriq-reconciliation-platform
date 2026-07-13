import re
from pathlib import Path


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}
SUPPORTED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
PRIVATE_KEY_PATTERN = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")
SECRET_PATTERN = re.compile(rb"(?i)(aws_secret_access_key|secret_key|api_key|password)\s*[:=]\s*[A-Za-z0-9_/\-+=]{12,}")


def validate_upload_metadata(filename: str, content_type: str | None) -> None:
    from fastapi import HTTPException, status

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload CSV or XLSX files only.",
        )
    if content_type and content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file content type. Upload a CSV or XLSX export.",
        )


def luhn_valid(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def detect_prohibited_sensitive_data(path: Path) -> bool:
    sample = path.read_bytes()[:512_000]
    if PRIVATE_KEY_PATTERN.search(sample) or SECRET_PATTERN.search(sample):
        return True
    text = sample.decode("utf-8", errors="ignore")
    headers = text.splitlines()[0].lower().split(",") if text.splitlines() else []
    if any(header.strip() in {"password", "passwd", "secret", "api_key", "private_key", "cvv", "cvc"} for header in headers):
        return True
    for candidate in re.findall(r"(?:\d[ -]?){13,19}", text):
        if luhn_valid(candidate):
            return True
    return False


def neutralize_spreadsheet_formula(value: object) -> object:
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return f"'{value}"
    return value
