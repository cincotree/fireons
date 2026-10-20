import re

from ingestion.parsers._text_utils import find_all_amounts, find_line, parse_date_abbrev_month

_INSURER_HEADER_RE = re.compile(r"^\s*([A-Z][A-Z ]+INSURANCE[A-Z .]*)\s*$")
_BOILERPLATE_WORDS = {"INSURANCE", "CO", "LTD", "LIMITED", "COMPANY", "PVT"}
_POLICY_NUMBER_RE = re.compile(r"Policy Number\s*:\s*([A-Z]*)(\d+)", re.IGNORECASE)
_POLICYHOLDER_RE = re.compile(r"Policyholder\s*:\s*(.+)", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"currency\s*:\s*(\w+)", re.IGNORECASE)
_GENERATED_ON_RE = re.compile(r"Statement Generated On\s*:\s*(.+)", re.IGNORECASE)
_FUND_SURRENDER_LABEL_RE = re.compile(r"Fund Value\s*Surrender Value", re.IGNORECASE)
_PURE_TERM_RE = re.compile(r"Pure Term Plan", re.IGNORECASE)


def _normalize_insurer_name(header: str) -> str | None:
    """'SAMPLE LIFE INSURANCE CO LTD' -> 'SampleLife' — strip known legal/product
    boilerplate words, title-case and concatenate what's left. Narrow, only proven
    against the one insurer name in the current eval corpus; a header this can't
    confidently reduce falls through (returns None) rather than guessing.
    """
    words = [w for w in header.strip().split() if w.upper() not in _BOILERPLATE_WORDS]
    if not words:
        return None
    return "".join(w.capitalize() for w in words)


def _extract_common(text: str) -> tuple[str, str, str, str] | None:
    """Returns (institution, identifier, currency, doc_issued_at_iso) or None."""
    lines = text.splitlines()
    if not lines:
        return None
    header_match = _INSURER_HEADER_RE.match(lines[0].strip())
    if header_match is None:
        return None
    institution = _normalize_insurer_name(header_match.group(1))
    if institution is None:
        return None

    policy_match = _POLICY_NUMBER_RE.search(text)
    if policy_match is None:
        return None
    identifier = policy_match.group(2)

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else None
    if currency is None:
        return None

    generated_hit = find_line(lines, _GENERATED_ON_RE)
    if generated_hit is None:
        return None
    generated_match = _GENERATED_ON_RE.search(generated_hit[1])
    doc_issued_at = parse_date_abbrev_month(generated_match.group(1)) if generated_match else None
    if doc_issued_at is None:
        return None

    return institution, identifier, currency, doc_issued_at.isoformat()


def try_parse_ulip(text: str) -> dict | None:
    if "Unit Linked Insurance Plan" not in text:
        return None
    common = _extract_common(text)
    if common is None:
        return None
    institution, identifier, currency, doc_issued_at = common

    lines = text.splitlines()
    label_hit = find_line(lines, _FUND_SURRENDER_LABEL_RE)
    if label_hit is None:
        return None
    label_index, _ = label_hit
    if label_index + 1 >= len(lines):
        return None
    amounts = find_all_amounts(lines[label_index + 1])
    if len(amounts) < 2:
        return None
    surrender_value = str(amounts[1])

    policyholder_match = _POLICYHOLDER_RE.search(text)
    investor_name = policyholder_match.group(1).strip() if policyholder_match else None
    warnings: list[str] = []
    if investor_name is None:
        warnings.append("could not find a policyholder name")

    as_of = doc_issued_at

    return {
        "document_type": "insurance_policy",
        "doc_issued_at": doc_issued_at,
        "investor_name": investor_name,
        "source": institution,
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": institution,
                "identifier": identifier,
                "instrument_name": None,
                "instrument_type": None,
                "units": None,
                "nav": None,
                "value": surrender_value,
                "currency": currency,
                "as_of": as_of,
            }
        ],
        "warnings": warnings,
    }


def try_parse_term_insurance(text: str) -> dict | None:
    if not _PURE_TERM_RE.search(text):
        return None
    common = _extract_common(text)
    if common is None:
        return None
    _institution, _identifier, _currency, doc_issued_at = common

    policyholder_match = _POLICYHOLDER_RE.search(text)
    investor_name = policyholder_match.group(1).strip() if policyholder_match else None

    return {
        "document_type": "insurance_policy",
        "doc_issued_at": doc_issued_at,
        "investor_name": investor_name,
        "source": None,
        "is_exhaustive": False,
        "holdings": [],
        "warnings": [],
    }
