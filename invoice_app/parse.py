from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class ParsedInvoiceFields:
    vendor: Optional[str]
    invoice_date: Optional[date]
    total_amount: Optional[float]
    currency: Optional[str]


_CURRENCY_SIGNS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
}


def _pick_vendor(text: str) -> Optional[str]:
    # Heuristic: vendor is often in the first few lines.
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in lines[:8]:
        if len(ln) >= 3 and len(ln) <= 60 and not re.search(r"\b(invoice|bill|tax)\b", ln, re.I):
            # Avoid pure numeric lines / IDs.
            if not re.fullmatch(r"[\d\W_]+", ln):
                return ln
    return None


def _pick_date(text: str) -> Optional[date]:
    # Try common formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD.MM.YYYY
    t = text or ""

    m = re.search(r"\b(20\d{2})[-/\.](\d{1,2})[-/\.](\d{1,2})\b", t)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d)

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", t)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Ambiguous: interpret as DD/MM unless it would be invalid.
        if a > 12:
            return date(y, b, a)
        if b > 12:
            return date(y, a, b)
        return date(y, b, a)

    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(20\d{2})\b", t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d)

    return None


def _pick_total(text: str) -> tuple[Optional[float], Optional[str]]:
    t = (text or "").replace("\u00a0", " ")

    # Prefer "Total" lines.
    total_line = None
    for line in t.splitlines():
        if re.search(r"\b(total|amount due|grand total)\b", line, re.I):
            total_line = line
            break
    haystack = total_line or t

    # Match currency + amount: "$ 1,234.56" or "EUR 1.234,56"
    m = re.search(
        r"(?P<cur>\$|€|£|USD|EUR|GBP)\s*"
        r"(?P<amt>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2}))",
        haystack,
        re.I,
    )
    if not m:
        return None, None

    cur_raw = m.group("cur").upper()
    currency = _CURRENCY_SIGNS.get(cur_raw, cur_raw)

    amt_raw = m.group("amt")
    # Normalize decimal separator:
    # - If both '.' and ',' exist, assume last one is decimal.
    if "." in amt_raw and "," in amt_raw:
        if amt_raw.rfind(".") > amt_raw.rfind(","):
            amt = float(amt_raw.replace(",", ""))
        else:
            amt = float(amt_raw.replace(".", "").replace(",", "."))
    else:
        # If only comma exists, treat as decimal.
        if "," in amt_raw and "." not in amt_raw:
            amt = float(amt_raw.replace(".", "").replace(",", "."))
        else:
            amt = float(amt_raw.replace(",", ""))

    return amt, currency


def parse_invoice_fields(text: str) -> ParsedInvoiceFields:
    vendor = _pick_vendor(text)
    inv_date = _pick_date(text)
    total_amount, currency = _pick_total(text)
    return ParsedInvoiceFields(
        vendor=vendor,
        invoice_date=inv_date,
        total_amount=total_amount,
        currency=currency,
    )

