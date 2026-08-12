import re

from ingestion.parsers._text_utils import (
    find_all_amounts,
    find_line,
    last_digits,
    parse_date_abbrev_month,
    parse_date_numeric,
)

_ACCOUNT_NO_RE = re.compile(r"account\s*no\.?\s*:?\s*([\dX]{9,18})", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"currency\s*:\s*(\w+)", re.IGNORECASE)
_CLOSING_BAL_LABEL_RE = re.compile(r"closing\s*bal", re.IGNORECASE)
_TO_DATE_NUMERIC_RE = re.compile(r"\bto\s*:?\s*(\d{2}[/-]\d{2}[/-]\d{4})", re.IGNORECASE)
_GENERATED_ON_RE = re.compile(r"generated\s*on\s*:?\s*(.+)", re.IGNORECASE)
_NAME_TITLE_RE = re.compile(
    r"^\s*(?:MR|MRS|MS|MISS|M/S|DR|SHRI|SMT|KUM)\.?\s+\S.*", re.IGNORECASE
)
_NAME_LABEL_RE = re.compile(r"customer\s*name\s*:\s*(.+)", re.IGNORECASE)
_PPF_RE = re.compile(r"provident\s*fund", re.IGNORECASE)
_EXCLUDED_MARKERS_RE = re.compile(
    r"loan\s*account|fd\s*account\s*no|rd\s*account\s*no", re.IGNORECASE
)


def _extract_common(text: str, institution: str, day_first: bool) -> dict | None:
    lines = text.splitlines()

    if _EXCLUDED_MARKERS_RE.search(text):
        return None

    account_match = _ACCOUNT_NO_RE.search(text)
    if account_match is None:
        return None
    identifier = last_digits(account_match.group(1))
    if not identifier:
        return None

    closing_bal_hit = find_line(lines, _CLOSING_BAL_LABEL_RE)
    if closing_bal_hit is None:
        return None
    label_index, _ = closing_bal_hit
    if label_index + 1 >= len(lines):
        return None
    amounts = find_all_amounts(lines[label_index + 1])
    if not amounts:
        return None
    value = str(amounts[-1])

    to_date_match = _TO_DATE_NUMERIC_RE.search(text)
    if to_date_match is None:
        return None
    as_of = parse_date_numeric(to_date_match.group(1), day_first=day_first)
    if as_of is None:
        return None

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else None
    if currency is None:
        return None

    warnings: list[str] = []

    doc_issued_at = as_of
    generated_match = find_line(lines, _GENERATED_ON_RE)
    if generated_match is not None:
        parsed = parse_date_abbrev_month(generated_match[1]) or parse_date_numeric(
            generated_match[1], day_first=day_first
        )
        if parsed is not None:
            doc_issued_at = parsed
        else:
            warnings.append("could not parse a generated-on date — used as_of instead")
    else:
        warnings.append("no generated-on date found — used as_of instead")

    investor_name = None
    for line in lines:
        if _NAME_TITLE_RE.match(line):
            investor_name = line.strip()
            break
    if investor_name is None:
        label_match = _NAME_LABEL_RE.search(text)
        if label_match:
            investor_name = label_match.group(1).strip()
    if investor_name is None:
        warnings.append("could not find an account holder name")

    instrument_type = "ppf" if _PPF_RE.search(text) else None

    return {
        "document_type": "bank_statement",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": investor_name,
        "source": institution,
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": institution,
                "identifier": identifier,
                "instrument_name": None,
                "instrument_type": instrument_type,
                "units": None,
                "nav": None,
                "value": value,
                "currency": currency,
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }


def try_parse_hdfc(text: str) -> dict | None:
    if "HDFC BANK LIMITED" not in text:
        return None
    return _extract_common(text, institution="HDFC", day_first=True)


def try_parse_icici(text: str) -> dict | None:
    if "ICICI BANK LIMITED" not in text:
        return None
    return _extract_common(text, institution="ICICI", day_first=True)


def try_parse_chase(text: str) -> dict | None:
    if "CHASE BANK" not in text:
        return None
    return _extract_common(text, institution="Chase", day_first=False)
