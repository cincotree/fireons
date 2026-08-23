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


# A different, real-world "Fixed Deposit Summary" export (confirmed: FD_Account.pdf)
# — a single table row, no bank name anywhere in the document at all (only a
# branch name). institution is genuinely absent here, not just hard to find —
# pipeline._account_name() treats that as a soft field and omits it from the
# account key rather than deferring this file to the LLM. No "generated on"
# date either; the Deposit Start Date is the best document-stated date
# available, used for both as_of and doc_issued_at.
_FD_SUMMARY_ROW_RE = re.compile(
    r"(\d+)\s+(\d{6,20})\s+(.+?)\s+([A-Z]{3})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+"
    r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+([\d.]+)\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})"
)
_FD_SUMMARY_NAME_RE = re.compile(r"^Name\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def try_parse_fd_summary(text: str) -> dict | None:
    if "Fixed Deposit Summary" not in text:
        return None
    if "Principal" not in text or "Maturity" not in text or "Deposit" not in text:
        return None

    normalized = re.sub(r"\s+", " ", text)
    row_match = _FD_SUMMARY_ROW_RE.search(normalized)
    if row_match is None:
        return None
    (
        _sr_no,
        account_no,
        _branch_and_holder,
        currency,
        principal,
        _maturity_amount,
        _maturity_date,
        _rate,
        deposit_start_date,
    ) = row_match.groups()

    as_of = parse_date_abbrev_month(deposit_start_date)
    if as_of is None:
        return None

    name_match = _FD_SUMMARY_NAME_RE.search(text)
    investor_name = name_match.group(1).strip() if name_match else None
    warnings = [
        f"{account_no}: institution could not be determined from this document "
        f"— rename the account once created"
    ]
    if investor_name is None:
        warnings.append("could not find an account holder name")

    return {
        "document_type": "deposit_statement",
        "doc_issued_at": as_of.isoformat(),
        "investor_name": investor_name,
        "source": None,
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": None,
                "identifier": account_no,
                "instrument_name": None,
                "instrument_type": "fd",
                "units": None,
                "nav": None,
                "value": principal.replace(",", ""),
                "currency": currency,
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }
