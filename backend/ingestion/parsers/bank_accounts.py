import re

from ingestion.parsers._text_utils import (
    find_all_amounts,
    find_line,
    last_digits,
    parse_date_abbrev_month,
    parse_date_numeric,
)

_ACCOUNT_NO_RE = re.compile(r"account\s*(?:no\.?|number)\s*:?\s*([\dX]{9,18})", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"currency\s*:\s*(\w+)", re.IGNORECASE)
_CLOSING_BAL_LABEL_RE = re.compile(r"closing\s*bal", re.IGNORECASE)
_TO_DATE_NUMERIC_RE = re.compile(r"\bto\s*:?\s*(\d{2}[/-]\d{2}[/-]\d{4})", re.IGNORECASE)
# Kotak's statement period has no "to" keyword at all — just "<start> - <end>"
# with abbreviated-month dates ("01 Jul 2026 - 31 Jul 2026") — the end date is
# the second date in that pair.
_PERIOD_END_ABBREV_RE = re.compile(
    r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s*-\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})"
)
_GENERATED_ON_RE = re.compile(r"generated\s*on\s*:?\s*(.+)", re.IGNORECASE)
_NAME_TITLE_RE = re.compile(
    r"^\s*(?:MR|MRS|MS|MISS|M/S|DR|SHRI|SMT|KUM)\.?\s+\S.*", re.IGNORECASE
)
_NAME_LABEL_RE = re.compile(r"customer\s*name\s*:\s*(.+)", re.IGNORECASE)
_PPF_RE = re.compile(r"provident\s*fund", re.IGNORECASE)
_EXCLUDED_MARKERS_RE = re.compile(
    r"loan\s*account|fd\s*account\s*no|rd\s*account\s*no", re.IGNORECASE
)


def _extract_common(
    text: str, institution: str, day_first: bool, default_currency: str | None = None
) -> dict | None:
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
    if to_date_match is not None:
        as_of = parse_date_numeric(to_date_match.group(1), day_first=day_first)
    else:
        period_end_match = _PERIOD_END_ABBREV_RE.search(text)
        as_of = (
            parse_date_abbrev_month(period_end_match.group(1)) if period_end_match else None
        )
    if as_of is None:
        return None

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else default_currency
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


_CHASE_BANK_RE = re.compile(r"chase\s+bank", re.IGNORECASE)


def try_parse_chase(text: str) -> dict | None:
    # Case-insensitive: a real Chase statement (JPMorgan Chase Bank, N.A.)
    # never prints "CHASE BANK" in that exact all-caps form — the original
    # exact-match check silently deferred every real Chase statement to the
    # LLM tier regardless of whether the rest of its layout was parseable.
    if not _CHASE_BANK_RE.search(text):
        return None
    return _extract_common(text, institution="Chase", day_first=False)


def try_parse_kotak(text: str) -> dict | None:
    if "Kotak Mahindra Bank" not in text:
        return None
    return _extract_common(text, institution="Kotak Mahindra Bank", day_first=True, default_currency="INR")


_SCB_STATEMENT_DATE_RE = re.compile(r"STATEMENT DATE\s*:\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})", re.IGNORECASE)
_SCB_TOTAL_LINE_RE = re.compile(r"^\s*Total\s", re.IGNORECASE)
_NAME_PAGE_SUFFIX_RE = re.compile(r"\s+Page\b.*$", re.IGNORECASE)


def try_parse_standard_chartered(text: str) -> dict | None:
    if "STANDARD CHART" not in text.upper():
        return None

    lines = text.splitlines()

    account_match = _ACCOUNT_NO_RE.search(text)
    if account_match is None:
        return None
    identifier = last_digits(account_match.group(1))
    if not identifier:
        return None

    statement_date_match = _SCB_STATEMENT_DATE_RE.search(text)
    if statement_date_match is None:
        return None
    as_of = parse_date_abbrev_month(statement_date_match.group(1))
    if as_of is None:
        return None

    total_hit = find_line(lines, _SCB_TOTAL_LINE_RE)
    if total_hit is None:
        return None
    amounts = find_all_amounts(total_hit[1])
    if not amounts:
        return None
    value = str(amounts[-1])

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else "INR"

    investor_name = None
    for line in lines:
        if _NAME_TITLE_RE.match(line):
            investor_name = _NAME_PAGE_SUFFIX_RE.sub("", line).strip()
            break
    warnings: list[str] = []
    if investor_name is None:
        warnings.append("could not find an account holder name")
    # A single-date bank statement (no separate "generated on" line) uses its
    # own statement date for both fields, matching the SGB/Morgan Stanley
    # precedent for documents whose only date is the document's own effective date.

    return {
        "document_type": "bank_statement",
        "doc_issued_at": as_of.isoformat(),
        "investor_name": investor_name,
        "source": "Standard Chartered Bank",
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": "Standard Chartered Bank",
                "identifier": identifier,
                "instrument_name": None,
                "instrument_type": None,
                "units": None,
                "nav": None,
                "value": value,
                "currency": currency,
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }
