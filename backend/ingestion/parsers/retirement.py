import re

from ingestion.parsers._text_utils import (
    find_all_amounts,
    find_line,
    parse_date_abbrev_month,
    parse_date_month_day_year,
)

_UAN_RE = re.compile(r"UAN\s*:\s*(\d+)", re.IGNORECASE)
_MEMBER_NAME_RE = re.compile(r"Member Name\s*:\s*(.+)", re.IGNORECASE)
_CLOSING_BALANCE_AS_ON_RE = re.compile(r"Closing Balance as on", re.IGNORECASE)
_PRINTED_ON_RE = re.compile(r"Printed On\s*:\s*(.+)", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"currency\s*:\s*(\w+)", re.IGNORECASE)


def try_parse_epf(text: str) -> dict | None:
    if "EMPLOYEES' PROVIDENT FUND ORGANISATION" not in text:
        return None

    lines = text.splitlines()

    uan_match = _UAN_RE.search(text)
    if uan_match is None:
        return None
    identifier = uan_match.group(1)

    balance_hit = find_line(lines, _CLOSING_BALANCE_AS_ON_RE)
    if balance_hit is None:
        return None
    amounts = find_all_amounts(balance_hit[1])
    if len(amounts) < 3:
        return None
    employee_balance, employer_balance, pension_balance = (str(a) for a in amounts[:3])

    printed_hit = find_line(lines, _PRINTED_ON_RE)
    if printed_hit is None:
        return None
    printed_match = _PRINTED_ON_RE.search(printed_hit[1])
    as_of = parse_date_abbrev_month(printed_match.group(1)) if printed_match else None
    if as_of is None:
        return None

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else None
    if currency is None:
        return None

    name_match = _MEMBER_NAME_RE.search(text)
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


_PRAN_RE = re.compile(r"PRAN\s*:\s*(\d+)", re.IGNORECASE)
_SUBSCRIBER_NAME_RE = re.compile(r"Subscriber Name\s*:\s*(.+)", re.IGNORECASE)
_HOLDINGS_AS_ON_RE = re.compile(r"Value of your Holdings.*as on\s*(.+?)\s*\(in", re.IGNORECASE)
_NPS_SCHEME_RE = re.compile(r"Scheme\s*:\s*(.+)", re.IGNORECASE)
_NPS_UNITS_NAV_VALUE_RE = re.compile(
    r"Closing Units\s*:\s*([\d,]+\.\d+)\s*NAV\s*:\s*([\d,]+\.\d+)\s*Value\s*:\s*([\d,]+\.\d+)",
    re.IGNORECASE,
)
_NPS_GENERATED_ON_RE = re.compile(r"Statement Generated On\s*:\s*(.+)", re.IGNORECASE)
_TIER_SUFFIX_RE = re.compile(r"\s*Tier\s*[I]+\s*$", re.IGNORECASE)


def try_parse_nps(text: str) -> dict | None:
    if "NATIONAL PENSION SYSTEM" not in text:
        return None

    lines = text.splitlines()

    pran_match = _PRAN_RE.search(text)
    if pran_match is None:
        return None
    identifier = pran_match.group(1)

    holdings_hit = find_line(lines, _HOLDINGS_AS_ON_RE)
    if holdings_hit is None:
        return None
    as_on_match = _HOLDINGS_AS_ON_RE.search(holdings_hit[1])
    as_of = parse_date_month_day_year(as_on_match.group(1)) if as_on_match else None
    if as_of is None:
        return None

    scheme_hit = find_line(lines, _NPS_SCHEME_RE)
    if scheme_hit is None:
        return None
    scheme_match = _NPS_SCHEME_RE.search(scheme_hit[1])
    if scheme_match is None:
        return None
    scheme_raw = scheme_match.group(1).split(" - ", 1)[-1].strip()
    scheme_raw = _TIER_SUFFIX_RE.sub("", scheme_raw)
    instrument_name = scheme_raw.replace(" ", "")
    if not instrument_name:
        return None

    units_hit = find_line(lines, _NPS_UNITS_NAV_VALUE_RE)
    if units_hit is None:
        return None
    units_match = _NPS_UNITS_NAV_VALUE_RE.search(units_hit[1])
    if units_match is None:
        return None
    units, nav, value = units_match.groups()

    generated_hit = find_line(lines, _NPS_GENERATED_ON_RE)
    if generated_hit is None:
        return None
    generated_match = _NPS_GENERATED_ON_RE.search(generated_hit[1])
    doc_issued_at = parse_date_abbrev_month(generated_match.group(1)) if generated_match else None
    if doc_issued_at is None:
        return None

    currency_match = _CURRENCY_RE.search(text)
    currency = currency_match.group(1).upper() if currency_match else None
    if currency is None:
        return None

    subscriber_match = _SUBSCRIBER_NAME_RE.search(text)
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
                "units": units.replace(",", ""),
                "nav": nav.replace(",", ""),
                "value": value.replace(",", ""),
                "currency": currency,
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }
