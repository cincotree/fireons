import re

from ingestion.parsers._text_utils import parse_date_abbrev_month

_ISSUE_REFERENCE_RE = re.compile(r"Issue Reference\s*:\s*(.+)", re.IGNORECASE)
_SETTLEMENT_DATE_RE = re.compile(
    r"Settlement Date\s*:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})", re.IGNORECASE
)
_UNITS_RE = re.compile(r"Number of Units \(In Grams\)\s*:\s*([\d,]+\.?\d*)", re.IGNORECASE)
_ISSUE_PRICE_RE = re.compile(r"Issue Price \(Rs\.\)\s*:\s*([\d,]+\.?\d*)", re.IGNORECASE)
_CONSIDERATION_RE = re.compile(r"Consideration Amount \(Rs\.\)\s*:\s*([\d,]+\.\d+)", re.IGNORECASE)
_INVESTOR_NAME_RE = re.compile(r"Investor Name\s*:\s*(.+)", re.IGNORECASE)


def _normalize_sgb_identifier(raw: str) -> str:
    """'SGB 2028 SERIES IV' -> 'SGB2028SeriesIV' — per the extraction schema's own
    worked example: short (<=3 char) alphabetic tokens are acronym-like and stay as
    printed, numeric tokens stay as printed, longer alphabetic tokens get
    title-cased. Spaces are always stripped.
    """
    tokens = raw.strip().split()
    normalized = []
    for token in tokens:
        if token.isdigit() or (token.isalpha() and len(token) <= 3):
            normalized.append(token)
        else:
            normalized.append(token.capitalize())
    return "".join(normalized)


def try_parse_sgb_confirmation(text: str) -> dict | None:
    if "RESERVE BANK OF INDIA" not in text or "Confirmation Receipt" not in text:
        return None

    issue_ref_match = _ISSUE_REFERENCE_RE.search(text)
    if issue_ref_match is None:
        return None
    identifier = _normalize_sgb_identifier(issue_ref_match.group(1))
    if not identifier:
        return None

    settlement_match = _SETTLEMENT_DATE_RE.search(text)
    if settlement_match is None:
        return None
    as_of = parse_date_abbrev_month(settlement_match.group(1))
    if as_of is None:
        return None

    units_match = _UNITS_RE.search(text)
    price_match = _ISSUE_PRICE_RE.search(text)
    consideration_match = _CONSIDERATION_RE.search(text)
    if not (units_match and consideration_match):
        return None

    investor_match = _INVESTOR_NAME_RE.search(text)
    investor_name = investor_match.group(1).strip() if investor_match else None
    warnings: list[str] = []
    if investor_name is None:
        warnings.append("could not find an investor name")
    # Not warning-worthy: a one-time RBI purchase confirmation never carries a
    # separate "statement generated on" line at all (unlike periodic statements) —
    # falling back to the settlement date here is the document's normal shape, not
    # a gap in this specific document.

    return {
        "document_type": "sgb_confirmation",
        "doc_issued_at": as_of.isoformat(),
        "investor_name": investor_name,
        "source": None,
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": None,
                "identifier": identifier,
                "instrument_name": None,
                "instrument_type": None,
                "units": units_match.group(1).replace(",", ""),
                "nav": price_match.group(1).replace(",", "") if price_match else None,
                "value": consideration_match.group(1).replace(",", ""),
                "currency": "INR",
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }
