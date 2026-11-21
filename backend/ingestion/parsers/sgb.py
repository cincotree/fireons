import re

from ingestion.parsers._text_utils import find_line, parse_date_abbrev_month

_ISSUE_REFERENCE_RE = re.compile(r"Issue Reference\s*:\s*(.+)", re.IGNORECASE)
_SETTLEMENT_DATE_RE = re.compile(
    r"Settlement Date\s*:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})", re.IGNORECASE
)
_UNITS_RE = re.compile(r"Number of Units \(In Grams\)\s*:\s*([\d,]+\.?\d*)", re.IGNORECASE)
_ISSUE_PRICE_RE = re.compile(r"Issue Price \(Rs\.\)\s*:\s*([\d,]+\.?\d*)", re.IGNORECASE)
_CONSIDERATION_RE = re.compile(r"Consideration Amount \(Rs\.\)\s*:\s*([\d,]+\.\d+)", re.IGNORECASE)
_INVESTOR_NAME_RE = re.compile(r"Investor Name\s*:\s*(.+)", re.IGNORECASE)

# RBI Retail Direct's actual confirmation receipt PDF prints labels and values as
# two separate blocks (a form layout), not "Label : value" lines — pdftotext just
# concatenates label after label, then value after value, with no colons at all.
# These markers locate the same fields positionally/by shape when the colon-based
# regexes above find nothing, rather than assuming the eval fixture's simplified
# single-line format.
_SGB_ISSUE_NAME_RE = re.compile(r"\bSGB\s+[\d\-]+\s+SERIES\s+[IVXLCDM]+\b", re.IGNORECASE)
_TWO_ABBREV_DATES_RE = re.compile(r"(\d{1,2}-[A-Za-z]{3}-\d{4})\s+(\d{1,2}-[A-Za-z]{3}-\d{4})")
_UNITS_PRICE_LINE_RE = re.compile(r"^\s*(\d+)\s+(\d+(?:\.\d+)?)\s*$")
_CONSIDERATION_AMOUNT_LINE_RE = re.compile(r"^\s*([\d,]+\.\d{2})\s*$")
_INVESTOR_ID_NAME_RE = re.compile(r"^\d{8,}\s+([A-Za-z][A-Za-z .]+)$")


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
    if "reserve bank of india" not in text.lower() or "confirmation receipt" not in text.lower():
        return None

    lines = text.splitlines()

    issue_ref_match = _ISSUE_REFERENCE_RE.search(text)
    if issue_ref_match is not None:
        identifier_raw = issue_ref_match.group(1)
    else:
        issue_name_match = _SGB_ISSUE_NAME_RE.search(text)
        identifier_raw = issue_name_match.group(0) if issue_name_match else None
    if not identifier_raw:
        return None
    identifier = _normalize_sgb_identifier(identifier_raw)
    if not identifier:
        return None

    settlement_match = _SETTLEMENT_DATE_RE.search(text)
    if settlement_match is not None:
        as_of = parse_date_abbrev_month(settlement_match.group(1))
    else:
        two_dates_match = _TWO_ABBREV_DATES_RE.search(text)
        as_of = parse_date_abbrev_month(two_dates_match.group(2)) if two_dates_match else None
    if as_of is None:
        return None

    units_match = _UNITS_RE.search(text)
    price_match = _ISSUE_PRICE_RE.search(text)
    consideration_match = _CONSIDERATION_RE.search(text)
    units_value = units_match.group(1).replace(",", "") if units_match else None
    price_value = price_match.group(1).replace(",", "") if price_match else None
    consideration_value = (
        consideration_match.group(1).replace(",", "") if consideration_match else None
    )

    if units_value is None or consideration_value is None:
        # The units/price pair sits on the line immediately above the
        # consideration amount in the form layout — anchoring on the amount
        # first avoids matching an earlier, unrelated two-number line (e.g.
        # "Security Code Subscription Serial") that fits the same shape.
        consideration_hit = find_line(lines, _CONSIDERATION_AMOUNT_LINE_RE)
        if consideration_hit is not None:
            consideration_index, consideration_line = consideration_hit
            if consideration_value is None:
                consideration_match_fallback = _CONSIDERATION_AMOUNT_LINE_RE.match(
                    consideration_line
                )
                if consideration_match_fallback is not None:
                    consideration_value = consideration_match_fallback.group(1).replace(",", "")
            if (units_value is None or price_value is None) and consideration_index > 0:
                up_match = _UNITS_PRICE_LINE_RE.match(lines[consideration_index - 1])
                if up_match is not None:
                    if units_value is None:
                        units_value = up_match.group(1)
                    if price_value is None:
                        price_value = up_match.group(2)
    if units_value is None or consideration_value is None:
        return None

    investor_match = _INVESTOR_NAME_RE.search(text)
    if investor_match is not None:
        investor_name = investor_match.group(1).strip()
    else:
        id_name_hit = find_line(lines, _INVESTOR_ID_NAME_RE)
        id_name_match = _INVESTOR_ID_NAME_RE.match(id_name_hit[1]) if id_name_hit else None
        investor_name = id_name_match.group(1).strip() if id_name_match else None
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
                "units": units_value,
                "nav": price_value,
                "value": consideration_value,
                "currency": "INR",
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }
