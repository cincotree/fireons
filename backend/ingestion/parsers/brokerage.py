import re
from datetime import date

from ingestion.parsers._text_utils import _MONTHS, find_line, parse_date_numeric

_CURRENCY_RE = re.compile(r"currency\s*:\s*(\w+)", re.IGNORECASE)
_GENERATED_ON_RE = re.compile(r"Statement Generated On\s*:\s*(\S+)", re.IGNORECASE)

# Morgan Stanley RSU — vested shares live in the plain HOLDINGS table row, read
# ONLY from that exact section; the STOCK PLAN SUMMARY/DETAILS sections further
# down the document hold unvested/potential value and are never touched at all,
# not even scanned, so there's no way to accidentally turn that into a position.
_MS_PERIOD_RE = re.compile(
    r"For the Period\s+([A-Za-z]+)\s+\d{1,2}-(\d{1,2}),\s*(\d{4})", re.IGNORECASE
)
_MS_STATEMENT_FOR_RE = re.compile(r"STATEMENT FOR\s*:\s*(.+)", re.IGNORECASE)
_MS_HOLDING_ROW_RE = re.compile(r"^(\S+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s*$")


def try_parse_morgan_stanley_rsu(text: str) -> dict | None:
    if "MORGAN STANLEY" not in text:
        return None

    lines = text.splitlines()

    period_match = _MS_PERIOD_RE.search(text)
    if period_match is None:
        return None
    month_name, end_day, year = period_match.groups()
    month = _MONTHS.get(month_name.lower()[:3])
    if month is None:
        return None
    try:
        as_of = date(int(year), month, int(end_day))
    except ValueError:
        return None

    holdings_hit = find_line(lines, re.compile(r"^\s*HOLDINGS\s*$"))
    if holdings_hit is None:
        return None
    holdings_index, _ = holdings_hit
    if holdings_index + 2 >= len(lines):
        return None
    row_match = _MS_HOLDING_ROW_RE.match(lines[holdings_index + 2].strip())
    if row_match is None:
        return None
    symbol, quantity, price, value = row_match.groups()

    generated_match = _GENERATED_ON_RE.search(text)
    if generated_match is None:
        return None
    doc_issued_at = parse_date_numeric(generated_match.group(1), day_first=False)
    if doc_issued_at is None:
        return None

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else None
    if currency is None:
        return None

    statement_for_match = _MS_STATEMENT_FOR_RE.search(text)
    investor_name = statement_for_match.group(1).strip() if statement_for_match else None
    warnings: list[str] = []
    if investor_name is None:
        warnings.append("could not find an account holder name")

    return {
        "document_type": "brokerage_statement",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": investor_name,
        "source": "Morgan Stanley",
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": None,
                "identifier": symbol,
                "instrument_name": None,
                "instrument_type": None,
                "units": quantity.replace(",", ""),
                "nav": price.replace(",", ""),
                "value": value.replace(",", ""),
                "currency": currency,
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }


_FIDELITY_PERIOD_RE = re.compile(
    r"Statement Period\s*:\s*\d{2}/\d{2}/\d{4}\s*-\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE
)
_FIDELITY_ACCOUNT_HOLDER_RE = re.compile(r"Account Holder\s*:\s*(.+)", re.IGNORECASE)
_FIDELITY_HOLDING_RE = re.compile(
    r"Symbol:\s*(\S+)\s*Quantity:\s*([\d,]+\.\d+)\s*Price \(\w+\):\s*([\d,]+\.\d+)\s*"
    r"Value \(\w+\):\s*([\d,]+\.\d+)",
    re.IGNORECASE,
)


def try_parse_fidelity(text: str) -> dict | None:
    if "FIDELITY INVESTMENTS" not in text:
        return None

    period_match = _FIDELITY_PERIOD_RE.search(text)
    if period_match is None:
        return None
    as_of = parse_date_numeric(period_match.group(1), day_first=False)
    if as_of is None:
        return None

    holding_match = _FIDELITY_HOLDING_RE.search(text)
    if holding_match is None:
        return None
    symbol, quantity, price, value = holding_match.groups()

    generated_match = _GENERATED_ON_RE.search(text)
    if generated_match is None:
        return None
    doc_issued_at = parse_date_numeric(generated_match.group(1), day_first=False)
    if doc_issued_at is None:
        return None

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else None
    if currency is None:
        return None

    holder_match = _FIDELITY_ACCOUNT_HOLDER_RE.search(text)
    investor_name = holder_match.group(1).strip() if holder_match else None
    warnings: list[str] = []
    if investor_name is None:
        warnings.append("could not find an account holder name")

    return {
        "document_type": "brokerage_statement",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": investor_name,
        "source": "Fidelity",
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": None,
                "identifier": symbol,
                "instrument_name": None,
                "instrument_type": None,
                "units": quantity.replace(",", ""),
                "nav": price.replace(",", ""),
                "value": value.replace(",", ""),
                "currency": currency,
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }
