import re

from ingestion.parsers._text_utils import parse_date_abbrev_month

_SECTION_INSTRUMENT_TYPES = {
    "EQUITY HOLDINGS": "equity",
    "REIT HOLDINGS": "reit",
    "INVIT HOLDINGS": "invit",
}
_ISIN_LINE_RE = re.compile(r"ISIN\s*:\s*\S+\s+.+\(NSE:\s*(\S+)\)", re.IGNORECASE)
_BALANCE_LINE_RE = re.compile(
    r"Closing Balance\s*:\s*([\d,]+\.\d+)\s*Closing Price\s*:\s*([\d,]+\.\d+)\s*"
    r"Value\s*:\s*([\d,]+\.\d+)",
    re.IGNORECASE,
)
_STATEMENT_PERIOD_RE = re.compile(
    r"Statement Period\s*:\s*\d{1,2}-[A-Za-z]{3}-\d{4}\s*to\s*(\d{1,2}-[A-Za-z]{3}-\d{4})",
    re.IGNORECASE,
)
_GENERATED_ON_RE = re.compile(r"Statement Generated On\s*:\s*(.+)", re.IGNORECASE)


def try_parse_demat_cas(text: str) -> dict | None:
    if "Depositories" not in text or "NSDL" not in text or "CDSL" not in text:
        return None
    if not any(marker in text for marker in _SECTION_INSTRUMENT_TYPES):
        return None

    lines = text.splitlines()

    period_match = _STATEMENT_PERIOD_RE.search(text)
    if period_match is None:
        return None
    as_of = parse_date_abbrev_month(period_match.group(1))
    if as_of is None:
        return None

    generated_match = _GENERATED_ON_RE.search(text)
    if generated_match is None:
        return None
    doc_issued_at = parse_date_abbrev_month(generated_match.group(1))
    if doc_issued_at is None:
        return None

    holdings = []
    current_instrument_type: str | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped in _SECTION_INSTRUMENT_TYPES:
            current_instrument_type = _SECTION_INSTRUMENT_TYPES[stripped]
            continue

        isin_match = _ISIN_LINE_RE.search(line)
        if isin_match is None or current_instrument_type is None:
            continue
        if index + 1 >= len(lines):
            return None
        balance_match = _BALANCE_LINE_RE.search(lines[index + 1])
        if balance_match is None:
            return None
        units, price, value = balance_match.groups()

        holdings.append(
            {
                "institution": None,
                "identifier": isin_match.group(1),
                "instrument_name": None,
                "instrument_type": current_instrument_type,
                "units": units.replace(",", ""),
                "nav": price.replace(",", ""),
                "value": value.replace(",", ""),
                "currency": "INR",
                "as_of": as_of.isoformat(),
            }
        )

    if not holdings:
        return None

    return {
        "document_type": "demat_cas",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": None,
        "source": "CDSL",
        "is_exhaustive": True,
        "holdings": holdings,
        "warnings": [],
    }
