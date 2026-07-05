import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def parse_money(value: object) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    cleaned = re.sub(r"^[A-Za-z]{3}\s*", "", text)
    cleaned = cleaned.replace(",", "").replace("$", "").replace("£", "").replace("€", "")
    try:
        amount = Decimal(cleaned)
        if not amount.is_finite():
            return None
        if negative:
            amount = -amount
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None
