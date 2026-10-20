import re
from decimal import Decimal, InvalidOperation

from ingestion.parsers._text_utils import (
    find_line,
    parse_date_abbrev_month,
    parse_date_month_day_year,
    parse_date_numeric,
)

_UAN_RE = re.compile(r"UAN\s*:?\s*(\d+)", re.IGNORECASE)
_MEMBER_NAME_RE = re.compile(r"Member Name\s*:\s*(.+)", re.IGNORECASE)
_MEMBER_ID_NAME_RE = re.compile(r"Member ID/Name\s*:?\s*\S+\s*/\s*(.+)", re.IGNORECASE)
_CLOSING_BALANCE_AS_ON_RE = re.compile(r"Closing Balance as on", re.IGNORECASE)
_PRINTED_ON_RE = re.compile(r"Printed On\s*:\s*(.+)", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"currency\s*:\s*(\w+)", re.IGNORECASE)


def try_parse_epf(text: str) -> dict | None:
    if "Member Passbook" not in text:
        return None

    lines = text.splitlines()

    uan_match = _UAN_RE.search(text)
    if uan_match is None:
        return None
    identifier = uan_match.group(1)

    balance_hit = find_line(lines, _CLOSING_BALANCE_AS_ON_RE)
    if balance_hit is None:
        return None
    # The official EPFO passbook export prints whole-rupee balances with no
    # decimal point ("2,29,892"), unlike the eval fixture's "210000.00" — a
    # decimal-requiring amount regex misses the real format entirely, so the
    # three trailing whitespace-separated tokens are taken directly instead.
    balance_tokens = balance_hit[1].split()[-3:]
    if len(balance_tokens) < 3:
        return None
    try:
        employee_balance, employer_balance, pension_balance = (
            str(Decimal(token.replace(",", ""))) for token in balance_tokens
        )
    except InvalidOperation:
        return None

    printed_hit = find_line(lines, _PRINTED_ON_RE)
    if printed_hit is None:
        return None
    printed_match = _PRINTED_ON_RE.search(printed_hit[1])
    as_of = None
    if printed_match is not None:
        as_of = parse_date_abbrev_month(printed_match.group(1))
        if as_of is None:
            as_of = parse_date_numeric(printed_match.group(1), day_first=True)
    if as_of is None:
        return None

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else "INR"

    name_match = _MEMBER_NAME_RE.search(text) or _MEMBER_ID_NAME_RE.search(text)
    investor_name = name_match.group(1).strip() if name_match else None
    warnings: list[str] = []
    if investor_name is None:
        warnings.append("could not find a member name")

    return {
        "document_type": "epf_passbook",
        "doc_issued_at": as_of.isoformat(),
        "investor_name": investor_name,
        "source": "EPFO",
        "is_exhaustive": True,
        "holdings": [
            {
                "institution": None,
                "identifier": identifier,
                "instrument_name": None,
                "instrument_type": None,
                "units": None,
                "nav": None,
                "value": None,
                "employee_balance": employee_balance,
                "employer_balance": employer_balance,
                "pension_balance": pension_balance,
                "currency": currency,
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }


_PRAN_RE = re.compile(r"PRAN\s*:?\s*(\d+)", re.IGNORECASE)
_SUBSCRIBER_NAME_RE = re.compile(r"Subscriber Name\s*:\s*(.+)", re.IGNORECASE)
_SUBSCRIBER_NAME_INLINE_RE = re.compile(r"Subscriber Name\s+([A-Z][A-Za-z ]+?)\s{2,}", re.IGNORECASE)
_HOLDINGS_AS_ON_RE = re.compile(
    r"Value of your Holdings.*?as on\s*(.+?)\s*\(in", re.IGNORECASE | re.DOTALL
)
_NPS_SCHEME_RE = re.compile(r"Scheme\s*:\s*(.+)", re.IGNORECASE)
_NPS_UNITS_NAV_VALUE_RE = re.compile(
    r"Closing Units\s*:\s*([\d,]+\.\d+)\s*NAV\s*:\s*([\d,]+\.\d+)\s*Value\s*:\s*([\d,]+\.\d+)",
    re.IGNORECASE,
)
_NPS_GENERATED_ON_RE = re.compile(r"Statement Generated On\s*:\s*(.+)", re.IGNORECASE)
_NPS_GENERATION_DATE_RE = re.compile(r"Statement Generation Date\s*:\s*(.+)", re.IGNORECASE)
_TIER_SUFFIX_RE = re.compile(r"\s*Tier\s*[I]+\s*$", re.IGNORECASE)
# The "NPS Transaction Statement" variant (CRA: NSDL/Protean) renders the
# per-scheme unit/NAV breakdown as a graphic table that pdftotext can't
# extract at all — only the account-level Investment Summary row survives as
# text: "<value> <num contributions> <total contribution> <withdrawal> <gain>".
_NPS_AGGREGATE_SUMMARY_RE = re.compile(
    r"^([\d,]+\.\d{2})\s+\d+\s+[\d,]+\.\d{2}\s+[\d,]+\.\d{2}\s+[\d,]+\.\d{2}\s*$"
)
_ACTIVE_TIER_RE = re.compile(r"Tier\s+(I{1,2})\s+Status\s+ACTIVE", re.IGNORECASE)


def try_parse_nps(text: str) -> dict | None:
    if "NATIONAL PENSION SYSTEM" not in text and "NPS TRANSACTION STATEMENT" not in text:
        return None

    lines = text.splitlines()

    pran_match = _PRAN_RE.search(text)
    if pran_match is None:
        return None
    identifier = pran_match.group(1)

    holdings_as_on_match = _HOLDINGS_AS_ON_RE.search(text)
    as_of = (
        parse_date_month_day_year(holdings_as_on_match.group(1))
        if holdings_as_on_match
        else None
    )
    if as_of is None:
        return None

    scheme_hit = find_line(lines, _NPS_SCHEME_RE)
    units_hit = find_line(lines, _NPS_UNITS_NAV_VALUE_RE) if scheme_hit else None
    if scheme_hit is not None and units_hit is not None:
        scheme_match = _NPS_SCHEME_RE.search(scheme_hit[1])
        if scheme_match is None:
            return None
        scheme_raw = scheme_match.group(1).split(" - ", 1)[-1].strip()
        scheme_raw = _TIER_SUFFIX_RE.sub("", scheme_raw)
        instrument_name = scheme_raw.replace(" ", "")
        if not instrument_name:
            return None

        units_match = _NPS_UNITS_NAV_VALUE_RE.search(units_hit[1])
        if units_match is None:
            return None
        units, nav, value = units_match.groups()
        units, nav, value = units.replace(",", ""), nav.replace(",", ""), value.replace(",", "")
    else:
        summary_hit = find_line(lines, _NPS_AGGREGATE_SUMMARY_RE)
        if summary_hit is None:
            return None
        summary_match = _NPS_AGGREGATE_SUMMARY_RE.match(summary_hit[1])
        if summary_match is None:
            return None
        value = summary_match.group(1).replace(",", "")
        units, nav = None, None

        tier_match = _ACTIVE_TIER_RE.search(text)
        instrument_name = f"Tier{tier_match.group(1)}" if tier_match else "TierI"

    generated_hit = find_line(lines, _NPS_GENERATED_ON_RE)
    generation_date_hit = find_line(lines, _NPS_GENERATION_DATE_RE) if generated_hit is None else None
    doc_issued_at = None
    if generated_hit is not None:
        generated_match = _NPS_GENERATED_ON_RE.search(generated_hit[1])
        doc_issued_at = (
            parse_date_abbrev_month(generated_match.group(1)) if generated_match else None
        )
    elif generation_date_hit is not None:
        generation_match = _NPS_GENERATION_DATE_RE.search(generation_date_hit[1])
        doc_issued_at = (
            parse_date_month_day_year(generation_match.group(1)) if generation_match else None
        )
    if doc_issued_at is None:
        return None

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else "INR"

    subscriber_match = _SUBSCRIBER_NAME_RE.search(text) or _SUBSCRIBER_NAME_INLINE_RE.search(text)
    investor_name = subscriber_match.group(1).strip() if subscriber_match else None
    warnings: list[str] = []
    if investor_name is None:
        warnings.append("could not find a subscriber name")

    return {
        "document_type": "nps_statement",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": investor_name,
        "source": "NPS",
        "is_exhaustive": True,
        "holdings": [
            {
                "institution": None,
                "identifier": identifier,
                "instrument_name": instrument_name,
                "instrument_type": None,
                "units": units,
                "nav": nav,
                "value": value,
                "currency": currency,
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }
