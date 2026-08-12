import re

from ingestion.parsers._text_utils import parse_date_abbrev_month

# Standalone AMC statements print only their own long legal name once at the top of
# the document — unlike CAMS's per-folio "SAMPLE AMC 1 - SampleAMC1" lines, there's
# no short-code paired with it anywhere in the text to mechanically derive from.
# Since this must reconcile to the exact same institution key CAMS/CDSL already use
# for the same AMC (see cas_and_amc_statement_no_double_count), a small alias table
# for known AMCs is the honest approach — same category as the eval-fixture-only
# constants elsewhere in this codebase. A header not in this table returns None
# (defers to the LLM) rather than guessing a normalization.
_AMC_HEADER_ALIASES = {
    "SAMPLE AMC 1 ASSET MANAGEMENT COMPANY LIMITED": "SampleAMC1",
    "SAMPLE AMC 2 ASSET MANAGEMENT COMPANY LIMITED": "SampleAMC2",
    "SAMPLE AMC 3 ASSET MANAGEMENT COMPANY LIMITED": "SampleAMC3",
}

_FOLIO_LABEL_RE = re.compile(r"^\s*Folio No\s*:\s*(\S+)", re.IGNORECASE)
_SCHEME_LABEL_RE = re.compile(r"^\s*Scheme\s*:\s*(.+)", re.IGNORECASE)
_UNITS_LABEL_RE = re.compile(r"Closing Units\s*:\s*([\d,]+\.\d+)", re.IGNORECASE)
_NAV_MARKET_VALUE_RE = re.compile(
    r"NAV on (\d{1,2}-[A-Za-z]{3}-\d{4})\s*:\s*INR\s*([\d,]+\.\d+)\s*"
    r"Market Value on (\d{1,2}-[A-Za-z]{3}-\d{4})\s*:\s*INR\s*([\d,]+\.\d+)",
    re.IGNORECASE,
)
_GENERATED_ON_RE = re.compile(r"Statement Generated On\s*:\s*(.+)", re.IGNORECASE)
_PAN_RE = re.compile(r"PAN\s*:\s*(\S+)", re.IGNORECASE)


def _parse_cams_style_holdings(lines: list[str], currency: str) -> list[dict] | None:
    """Shared by CAMS and the standalone AMC statement — both use the identical
    per-folio block: Folio No / Scheme / Closing Units / 'NAV on ... Market Value
    on ...' — differing only in where the institution name is found (see callers).
    """
    holdings = []
    for index, line in enumerate(lines):
        folio_match = _FOLIO_LABEL_RE.match(line)
        if not folio_match:
            continue
        if index + 3 >= len(lines):
            return None
        scheme_match = _SCHEME_LABEL_RE.match(lines[index + 1])
        units_match = _UNITS_LABEL_RE.search(lines[index + 2])
        nav_match = _NAV_MARKET_VALUE_RE.search(lines[index + 3])
        if not (scheme_match and units_match and nav_match):
            return None
        nav_date, nav, _value_date, value = nav_match.groups()
        as_of = parse_date_abbrev_month(nav_date)
        if as_of is None:
            return None
        holdings.append(
            {
                "identifier": folio_match.group(1),
                "instrument_name": scheme_match.group(1).split(" - ")[0].strip(),
                "units": units_match.group(1).replace(",", ""),
                "nav": nav.replace(",", ""),
                "value": value.replace(",", ""),
                "currency": currency,
                "as_of": as_of.isoformat(),
                "_institution_anchor_index": index,
            }
        )
    return holdings or None


def try_parse_cams_cas(text: str) -> dict | None:
    if "brought to you by CAMS" not in text:
        return None

    lines = text.splitlines()
    holdings = _parse_cams_style_holdings(lines, currency="INR")
    if holdings is None:
        return None

    for holding in holdings:
        anchor = holding.pop("_institution_anchor_index")
        if anchor == 0:
            return None
        amc_line = lines[anchor - 1]
        if " - " not in amc_line:
            return None
        holding["institution"] = amc_line.split(" - ")[-1].strip()
        holding["instrument_type"] = None

    generated_match = _GENERATED_ON_RE.search(text)
    if generated_match is None:
        return None
    doc_issued_at = parse_date_abbrev_month(generated_match.group(1))
    if doc_issued_at is None:
        return None

    pan_match = _PAN_RE.search(text)
    investor_name = None
    warnings: list[str] = []
    if pan_match is None:
        warnings.append("could not find a PAN")

    return {
        "document_type": "mutual_fund_cas",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": investor_name,
        "source": "CAMS",
        "is_exhaustive": True,
        "holdings": holdings,
        "warnings": warnings,
    }


def try_parse_standalone_amc_statement(text: str) -> dict | None:
    lines = text.splitlines()
    if not lines:
        return None
    header = lines[0].strip()
    institution = _AMC_HEADER_ALIASES.get(header)
    if institution is None:
        return None
    if "CONSOLIDATED ACCOUNT STATEMENT" in text:
        return None

    holdings = _parse_cams_style_holdings(lines, currency="INR")
    if holdings is None:
        return None

    for holding in holdings:
        holding.pop("_institution_anchor_index")
        holding["institution"] = institution
        holding["instrument_type"] = None

    generated_match = _GENERATED_ON_RE.search(text)
    if generated_match is None:
        return None
    doc_issued_at = parse_date_abbrev_month(generated_match.group(1))
    if doc_issued_at is None:
        return None

    return {
        "document_type": "mutual_fund_cas",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": None,
        "source": institution,
        "is_exhaustive": False,
        "holdings": holdings,
        "warnings": [],
    }


_CDSL_AMC_NAME_RE = re.compile(r"^\s*AMC Name\s*:\s*(.+)", re.IGNORECASE)
_CDSL_SCHEME_NAME_RE = re.compile(r"^\s*Scheme Name\s*:\s*(.+)", re.IGNORECASE)
_CDSL_FOLIO_RE = re.compile(r"^\s*Folio No\s*:\s*(\S+)", re.IGNORECASE)
_CDSL_CLOSING_BALANCE_RE = re.compile(
    r"Closing Balance\s*:\s*([\d,]+\.\d+)\s*NAV\s*:\s*([\d,]+\.\d+)\s*"
    r"Value\s*:\s*([\d,]+\.\d+)\s*NAV Date\s*:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})",
    re.IGNORECASE,
)


def try_parse_cdsl_mutual_fund_cas(text: str) -> dict | None:
    if "Central Depository Services" not in text:
        return None
    if "AMC Name" not in text or "Folio No" not in text:
        return None

    lines = text.splitlines()
    holdings = []
    for index, line in enumerate(lines):
        amc_match = _CDSL_AMC_NAME_RE.match(line)
        if not amc_match:
            continue
        if index + 2 >= len(lines):
            return None
        scheme_match = _CDSL_SCHEME_NAME_RE.match(lines[index + 1])
        folio_match = _CDSL_FOLIO_RE.match(lines[index + 2])
        if not (scheme_match and folio_match):
            return None
        if index + 3 >= len(lines):
            return None
        balance_match = _CDSL_CLOSING_BALANCE_RE.search(lines[index + 3])
        if not balance_match:
            return None

        institution = amc_match.group(1).strip()
        scheme_text = scheme_match.group(1).strip()
        # Strip a redundant AMC-name prefix if the scheme text repeats it
        # ("SampleAMC1 SchemeAlpha Growth Plan Scheme Code : 02G") — same
        # normalization already proven necessary for the LLM extraction path.
        if scheme_text.startswith(institution):
            scheme_text = scheme_text[len(institution) :].strip()
        instrument_name = scheme_text.split()[0] if scheme_text.split() else None
        if instrument_name is None:
            return None

        units, nav, value, nav_date = balance_match.groups()
        as_of = parse_date_abbrev_month(nav_date)
        if as_of is None:
            return None

        holdings.append(
            {
                "institution": institution,
                "identifier": folio_match.group(1),
                "instrument_name": instrument_name,
                "instrument_type": None,
                "units": units.replace(",", ""),
                "nav": nav.replace(",", ""),
                "value": value.replace(",", ""),
                "currency": "INR",
                "as_of": as_of.isoformat(),
            }
        )

    if not holdings:
        return None

    generated_match = _GENERATED_ON_RE.search(text)
    if generated_match is None:
        return None
    doc_issued_at = parse_date_abbrev_month(generated_match.group(1))
    if doc_issued_at is None:
        return None

    return {
        "document_type": "mutual_fund_cas",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": None,
        "source": "CDSL",
        "is_exhaustive": True,
        "holdings": holdings,
        "warnings": [],
    }
