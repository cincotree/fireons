import re

from ingestion.parsers._text_utils import find_all_amounts, find_line, parse_date_abbrev_month

_LOAN_ACCOUNT_NO_RE = re.compile(r"loan\s*account\s*no\s*:?\s*LN(\d+)", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"currency\s*:\s*(\w+)", re.IGNORECASE)
_OUTSTANDING_LABEL_RE = re.compile(r"outstanding\s*principal", re.IGNORECASE)
_GENERATED_ON_RE = re.compile(r"generated\s*on\s*:?\s*(.+)", re.IGNORECASE)
_NAME_TITLE_RE = re.compile(
    r"^\s*(?:MR|MRS|MS|MISS|M/S|DR|SHRI|SMT|KUM)\.?\s+\S.*", re.IGNORECASE
)


def try_parse_loan_statement(text: str) -> dict | None:
    if "HDFC BANK LIMITED" not in text or "Loan Account Statement" not in text:
        return None

    lines = text.splitlines()

    account_match = _LOAN_ACCOUNT_NO_RE.search(text)
    if account_match is None:
        return None
    identifier = account_match.group(1)

    label_hit = find_line(lines, _OUTSTANDING_LABEL_RE)
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
        warnings.append("could not find an account holder name")

    return {
        "document_type": "loan_statement",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": investor_name,
        "source": "HDFC",
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": "HDFC",
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
