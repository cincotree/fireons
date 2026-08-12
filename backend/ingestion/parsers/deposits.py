import re

from ingestion.parsers._text_utils import find_all_amounts, find_line, parse_date_abbrev_month

_CURRENCY_RE = re.compile(r"currency\s*:\s*(\w+)", re.IGNORECASE)
_FD_ACCOUNT_NO_RE = re.compile(r"fd\s*account\s*no\s*:?\s*FD(\d+)", re.IGNORECASE)
_RD_ACCOUNT_NO_RE = re.compile(r"rd\s*account\s*no\s*:?\s*RD(\d+)", re.IGNORECASE)
_CURRENT_VALUE_LABEL_RE = re.compile(r"current\s*value", re.IGNORECASE)
_GENERATED_ON_RE = re.compile(r"generated\s*on\s*:?\s*(.+)", re.IGNORECASE)
_NAME_TITLE_RE = re.compile(
    r"^\s*(?:MR|MRS|MS|MISS|M/S|DR|SHRI|SMT|KUM)\.?\s+\S.*", re.IGNORECASE
)
_NAME_LABEL_RE = re.compile(r"customer\s*name\s*:\s*(.+)", re.IGNORECASE)


def _extract_deposit(
    text: str, *, instrument_type: str, institution: str, account_no_re: re.Pattern
) -> dict | None:
    lines = text.splitlines()

    account_match = account_no_re.search(text)
    if account_match is None:
        return None
    identifier = account_match.group(1)

    label_hit = find_line(lines, _CURRENT_VALUE_LABEL_RE)
    if label_hit is None:
        return None
    label_index, _ = label_hit
    if label_index + 1 >= len(lines):
        return None
    amounts = find_all_amounts(lines[label_index + 1])
    if not amounts:
        return None
    value = str(amounts[-1])

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else None
    if currency is None:
        return None

    warnings: list[str] = []

    generated_hit = find_line(lines, _GENERATED_ON_RE)
    as_of = None
    if generated_hit is not None:
        as_of = parse_date_abbrev_month(generated_hit[1])
    if as_of is None:
        warnings.append("could not find a generated-on date")
        return None
    doc_issued_at = as_of

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

    return {
        "document_type": "deposit_statement",
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


def try_parse_fd(text: str) -> dict | None:
    if "Fixed Deposit Account Statement" not in text or "HDFC BANK LIMITED" not in text:
        return None
    return _extract_deposit(
        text, instrument_type="fd", institution="HDFC", account_no_re=_FD_ACCOUNT_NO_RE
    )


def try_parse_rd(text: str) -> dict | None:
    if "Recurring Deposit Account Statement" not in text or "ICICI BANK LIMITED" not in text:
        return None
    return _extract_deposit(
        text, instrument_type="rd", institution="ICICI", account_no_re=_RD_ACCOUNT_NO_RE
    )
