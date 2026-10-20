import re
from datetime import date

from ingestion.parsers._text_utils import _MONTHS, parse_date_abbrev_month

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

# Some CAMS documents print a "/ N" sub-folio suffix with a space before it
# ("19702068 / 0"), others without ("19702068/0", e.g. the KFinTech summary and
# CDSL formats) — captured together and whitespace-stripped at the call site so
# both forms normalize to the identical identifier ("19702068/0"), otherwise the
# same real folio gets two different account keys depending on which document
# it came from (confirmed against real documents: CAS_CAMS.pdf vs
# CAS_KFinTech.pdf silently double-counted the same fund).
_FOLIO_LABEL_RE = re.compile(r"^\s*Folio No\s*:\s*(\S+(?:\s*/\s*\d+)?)", re.IGNORECASE)
_SCHEME_LABEL_RE = re.compile(r"^\s*Scheme\s*:\s*(.+)", re.IGNORECASE)
_UNITS_LABEL_RE = re.compile(r"Closing Units\s*:\s*([\d,]+\.\d+)", re.IGNORECASE)
_NAV_MARKET_VALUE_RE = re.compile(
    r"NAV on (\d{1,2}-[A-Za-z]{3}-\d{4})\s*:\s*INR\s*([\d,]+\.\d+)\s*"
    r"Market Value on (\d{1,2}-[A-Za-z]{3}-\d{4})\s*:\s*INR\s*([\d,]+\.\d+)",
    re.IGNORECASE,
)
_GENERATED_ON_RE = re.compile(r"Statement Generated On\s*:\s*(.+)", re.IGNORECASE)
_PAN_RE = re.compile(r"PAN\s*:\s*(\S+)", re.IGNORECASE)

# Real CAMS statements print the AMC's name once as a standalone line above a
# group of one or more folios ("Aditya Birla Sun Life Mutual Fund"), not
# per-folio — unlike the short-code "SAMPLE AMC 1 - SampleAMC1" line the eval
# fixtures use directly above each Folio No. Both are handled: the short-code
# form first (unchanged, anchor-1 lookup), falling back to the nearest
# preceding "... Mutual Fund" header line for real-world documents. Some AMCs
# print an abbreviated "NAVI MF" form instead of the full "Navi Mutual Fund" —
# confirmed on a real document that this was silently missed, letting the
# forward-fill carry the PREVIOUS (wrong) AMC name into the abbreviated
# section's folios instead of updating to the correct one.
_AMC_MUTUAL_FUND_HEADER_RE = re.compile(r"^[A-Za-z][\w &.,'()/-]*\b(?:Mutual Fund|MF)$")


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
                "identifier": folio_match.group(1).replace(" ", ""),
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


_PAN_KYC_MARKER_RE = re.compile(r"^PAN:\s*\S+.*PAN:\s*OK", re.IGNORECASE)
_CLOSING_UNIT_BALANCE_RE = re.compile(r"Closing Unit Balance:\s*([\d,]+\.\d+)", re.IGNORECASE)
_SCHEME_CODE_PREFIX_RE = re.compile(r"^[A-Za-z0-9]+-")
# The "Non-Demat" suffix appears in at least three raw forms across real
# documents: "(Non-Demat)" (hyphen, no space), "(Non Demat)" (space, no
# hyphen — the KFinTech summary's own native formatting for some rows), and
# "(Non -Demat)" (hyphen preceded by a space — a line-wrap artifact: the raw
# text wraps as "(Non\n-Demat)" and joining lines with a space introduces the
# space). Confirmed on real documents: the same fund read from two documents
# where the suffix wrapped differently produced two different account keys.
# [\s-]* between "Non" and "Demat" absorbs any combination of the three.
_SCHEME_NAME_CUTOFF_RE = re.compile(r"\s*\(Non[\s-]*Demat\)|\s*-\s*ISIN|\bISIN\s*:", re.IGNORECASE)


def _normalize_scheme_hyphens(text: str) -> str:
    """A scheme name can wrap at any hyphen ("...Plan-\\nGrowth"), and joining
    lines with a space then leaves a stray space on whichever side of the
    hyphen the wrap happened to fall — different per document/parser, since
    CAMS's, KFinTech's, and Navi's own tables all wrap (or don't) at different
    points for the identical fund. Collapsing all hyphen-adjacent whitespace
    to a single canonical form (no space either side) makes every parser
    converge on the same instrument_name instead of splitting into separate
    account keys. Confirmed on real documents twice: "Bandhan Liquid
    Fund-Direct Plan-Growth" (CAMS, no wrap) vs "...Plan- Growth" (KFinTech,
    wrapped right after the hyphen); and the standalone Navi statement parser
    (which never wraps, spaces intact) vs CAMS/KFinTech for the same Navi
    fund once those two started stripping the spaces and it didn't.
    Called by every parser in this module that extracts a scheme name.
    """
    return re.sub(r"\s*-\s*", "-", text)


def _clean_real_scheme_name(scheme_text: str) -> str | None:
    text = _SCHEME_CODE_PREFIX_RE.sub("", scheme_text, count=1)
    cutoff = _SCHEME_NAME_CUTOFF_RE.search(text)
    if cutoff:
        text = text[: cutoff.start()]
    text = _normalize_scheme_hyphens(text)
    text = text.strip(" -")
    return text or None


def _parse_cams_real_holdings(lines: list[str]) -> list[dict] | None:
    """Real CAMS statements print the scheme description as free text directly
    above 'Folio No:' (preceded by a 'PAN: ... PAN: OK' marker line, not a
    labelled 'Scheme :' line), and the closing balance as 'Closing Unit
    Balance: ...' later in the same folio's block, after disclaimer text —
    a materially different layout from the eval fixtures' labelled format
    that _parse_cams_style_holdings expects.
    """
    folio_indices = [index for index, line in enumerate(lines) if _FOLIO_LABEL_RE.match(line)]
    if not folio_indices:
        return None

    holdings = []
    for position, start in enumerate(folio_indices):
        end = folio_indices[position + 1] if position + 1 < len(folio_indices) else len(lines)
        block = lines[start:end]

        folio_match = _FOLIO_LABEL_RE.match(block[0])
        if not folio_match:
            return None

        marker_index = None
        for index in range(start - 1, max(start - 6, -1), -1):
            if _PAN_KYC_MARKER_RE.match(lines[index].strip()):
                marker_index = index
                break
        if marker_index is None:
            return None
        scheme_text = " ".join(line.strip() for line in lines[marker_index + 1 : start])
        instrument_name = _clean_real_scheme_name(scheme_text)
        if instrument_name is None:
            return None

        nav_match = next((m for line in block if (m := _NAV_MARKET_VALUE_RE.search(line))), None)
        closing_match = next(
            (m for line in block if (m := _CLOSING_UNIT_BALANCE_RE.search(line))), None
        )
        if nav_match is None or closing_match is None:
            return None
        nav_date, nav, _value_date, value = nav_match.groups()
        as_of = parse_date_abbrev_month(nav_date)
        if as_of is None:
            return None

        holdings.append(
            {
                "identifier": folio_match.group(1).replace(" ", ""),
                "instrument_name": instrument_name,
                "units": closing_match.group(1).replace(",", ""),
                "nav": nav.replace(",", ""),
                "value": value.replace(",", ""),
                "currency": "INR",
                "as_of": as_of.isoformat(),
                "_institution_anchor_index": start,
            }
        )
    return holdings or None


def try_parse_cams_cas(text: str) -> dict | None:
    if "brought to you by CAMS" not in text:
        return None

    lines = text.splitlines()
    holdings = _parse_cams_style_holdings(lines, currency="INR")
    if holdings is None:
        holdings = _parse_cams_real_holdings(lines)
    if holdings is None:
        return None

    current_amc_header: str | None = None
    amc_header_as_of: dict[int, str | None] = {}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if _AMC_MUTUAL_FUND_HEADER_RE.match(stripped):
            # Normalize the abbreviated "NAVI MF" form to the same "Navi Mutual
            # Fund" string every other parser uses for this AMC (the KFinTech
            # summary's alias table, the standalone Navi statement parser) —
            # otherwise the identical real-world folio ends up keyed under two
            # different institution strings depending on which document it's
            # read from, and silently double-counts instead of deduping.
            if stripped.endswith(" MF") and not stripped.endswith("Mutual Fund"):
                current_amc_header = f"{stripped[:-len(' MF')].title()} Mutual Fund"
            else:
                current_amc_header = stripped
        amc_header_as_of[index] = current_amc_header

    for holding in holdings:
        anchor = holding.pop("_institution_anchor_index")
        institution = None
        if anchor > 0:
            amc_line = lines[anchor - 1]
            if " - " in amc_line and "ISIN" not in amc_line:
                institution = amc_line.split(" - ")[-1].strip()
        if institution is None:
            institution = amc_header_as_of.get(anchor)
        if institution is None:
            return None
        holding["institution"] = institution
        holding["instrument_type"] = None

    generated_match = _GENERATED_ON_RE.search(text)
    if generated_match is not None:
        doc_issued_at = parse_date_abbrev_month(generated_match.group(1))
        if doc_issued_at is None:
            return None
    else:
        as_of_dates = [date.fromisoformat(holding["as_of"]) for holding in holdings]
        if not as_of_dates:
            return None
        doc_issued_at = max(as_of_dates)

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
# Same "/ N" spacing normalization as _FOLIO_LABEL_RE above.
_CDSL_FOLIO_RE = re.compile(r"^\s*Folio No\s*:\s*(\S+(?:\s*/\s*\d+)?)", re.IGNORECASE)
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
                "identifier": folio_match.group(1).replace(" ", ""),
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


# CAMS's "Consolidated Account Summary" (combining CAMS- and KFinTech-registered
# folios into one table) is a distinct document from the transactional CAS above —
# no per-folio labels at all, one row per fund: "<folio> <value><code> - <name...
# wrapped across 1-3 lines...>" then a trailer line "<units> <nav date> <nav>
# <CAMS|KFINTECH><isin> <cost value>". No AMC-name header lines either, so the
# institution is derived from a small known-AMC-prefix table — same idiom as
# _AMC_HEADER_ALIASES above, longest prefix first. An AMC not in the table falls
# back to None, which quarantines just that holding's document assignment by
# returning None for the whole parse (defers to the LLM) rather than guessing.
_SUMMARY_ROW_START_RE = re.compile(r"^([\w/]+)\s+([\d,]+\.\d+)([A-Za-z0-9]+)\s*-\s*(.+)$")
_SUMMARY_ROW_TRAILER_RE = re.compile(
    r"^([\d,]+\.\d+)\s+(\d{1,2}-[A-Za-z]{3}-\d{4})\s+([\d,]+\.\d+)\s+"
    r"(CAMS|KFINTECH)([A-Z0-9]+)\s+([\d,]+\.\d+)\s*$"
)
_SUMMARY_AS_ON_RE = re.compile(r"Consolidated Account Summary\s*As on\s*(\d{1,2}-[A-Za-z]{3}-\d{4})")
_KNOWN_AMC_PREFIXES = [
    ("Aditya Birla Sun Life", "Aditya Birla Sun Life Mutual Fund"),
    ("Bank of India", "Bank of India Mutual Fund"),
    ("Baroda BNP Paribas", "Baroda BNP Paribas Mutual Fund"),
    ("Canara Robeco", "Canara Robeco Mutual Fund"),
    ("ICICI Prudential", "ICICI Prudential Mutual Fund"),
    ("Invesco India", "Invesco Mutual Fund"),
    ("Mirae Asset", "Mirae Asset Mutual Fund"),
    ("Motilal Oswal", "Motilal Oswal Mutual Fund"),
    ("Nippon India", "Nippon India Mutual Fund"),
    ("PGIM India", "PGIM India Mutual Fund"),
    ("Parag Parikh", "PPFAS Mutual Fund"),
    ("PPFAS", "PPFAS Mutual Fund"),
    ("Bandhan", "Bandhan Mutual Fund"),
    ("Axis", "Axis Mutual Fund"),
    ("DSP", "DSP Mutual Fund"),
    ("Franklin", "Franklin Templeton Mutual Fund"),
    ("HDFC", "HDFC Mutual Fund"),
    ("JM", "JM Financial Mutual Fund"),
    ("Kotak", "Kotak Mutual Fund"),
    ("Navi", "Navi Mutual Fund"),
    ("quant", "quant Mutual Fund"),
    ("SBI", "SBI Mutual Fund"),
    ("Union", "Union Mutual Fund"),
    ("UTI", "UTI Mutual Fund"),
]


def _match_known_amc(scheme_text: str) -> str | None:
    for prefix, institution in _KNOWN_AMC_PREFIXES:
        if scheme_text.lower().startswith(prefix.lower()):
            return institution
    return None


def try_parse_cams_kfintech_summary(text: str) -> dict | None:
    if "CAMS and KFintech" not in text:
        return None

    lines = text.splitlines()
    as_on_match = _SUMMARY_AS_ON_RE.search(text)
    if as_on_match is None:
        return None
    doc_issued_at = parse_date_abbrev_month(as_on_match.group(1))
    if doc_issued_at is None:
        return None

    holdings = []
    for index, line in enumerate(lines):
        start_match = _SUMMARY_ROW_START_RE.match(line)
        if not start_match:
            continue
        folio, market_value, _code, name_start = start_match.groups()

        trailer_index = None
        for candidate_index in range(index, min(index + 5, len(lines))):
            if _SUMMARY_ROW_TRAILER_RE.match(lines[candidate_index]):
                trailer_index = candidate_index
                break
        if trailer_index is None:
            return None
        trailer_match = _SUMMARY_ROW_TRAILER_RE.match(lines[trailer_index])

        continuation = lines[index + 1 : trailer_index]
        scheme_text = " ".join([name_start, *continuation]).strip()
        institution = _match_known_amc(scheme_text)
        if institution is None:
            return None

        units, nav_date, nav, _registrar, _isin, _cost_value = trailer_match.groups()
        as_of = parse_date_abbrev_month(nav_date)
        if as_of is None:
            return None

        instrument_name = _clean_real_scheme_name(scheme_text)
        if instrument_name is None:
            return None

        holdings.append(
            {
                "institution": institution,
                "identifier": folio,
                "instrument_name": instrument_name,
                "instrument_type": None,
                "units": units.replace(",", ""),
                "nav": nav.replace(",", ""),
                "value": market_value.replace(",", ""),
                "currency": "INR",
                "as_of": as_of.isoformat(),
            }
        )

    if not holdings:
        return None

    return {
        "document_type": "mutual_fund_cas",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": None,
        "source": "CAMS+KFinTech",
        "is_exhaustive": True,
        "holdings": holdings,
        "warnings": [],
    }


# Navi's (and similarly-templated AMCs') own "Account Statement" export — a
# single-scheme statement, distinct from both the CAMS CAS and the generic
# _AMC_HEADER_ALIASES standalone-AMC template above (no recognizable AMC
# legal-name header line at all; the first line is a print-job artifact).
# Its PORTFOLIO SUMMARY row is column-scrambled by pdftotext with values
# glued directly onto adjacent text/numbers, and its date fields print with a
# stray space before the hyphen ("08-Aug -2026") that the shared
# parse_date_abbrev_month helper's single-separator assumption rejects.
_NAVI_FOLIO_RE = re.compile(r"Folio Number\s*:\s*(\S+)", re.IGNORECASE)
_NAVI_STATEMENT_DATE_RE = re.compile(
    r"Statement Date\s*:\s*(\d{1,2})-([A-Za-z]{3})\s*-\s*(\d{4})", re.IGNORECASE
)
_NAVI_INVESTOR_NAME_RE = re.compile(r"Investor Name\s*:\s*(.+)", re.IGNORECASE)
_NAVI_ROW_RE = re.compile(
    r"([\d.]+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d{2})(.+?)\s+"
    r"([\d,]+\.\d{2})(\d{1,2}-[A-Za-z]{3}-\d{4})\s+([\d,.]+)"
)


def _parse_navi_date(day: str, month_abbrev: str, year: str) -> date | None:
    month = _MONTHS.get(month_abbrev.lower())
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def try_parse_navi_account_statement(text: str) -> dict | None:
    if "Navi Mutual Fund" not in text or "PORTFOLIO SUMMARY" not in text:
        return None

    folio_match = _NAVI_FOLIO_RE.search(text)
    if folio_match is None:
        return None
    identifier = folio_match.group(1).strip()

    statement_date_match = _NAVI_STATEMENT_DATE_RE.search(text)
    if statement_date_match is None:
        return None
    doc_issued_at = _parse_navi_date(*statement_date_match.groups())
    if doc_issued_at is None:
        return None

    row_match = _NAVI_ROW_RE.search(text)
    if row_match is None:
        return None
    nav, units, current_value, scheme_name, _cost, nav_date_str, _idcw = row_match.groups()
    as_of = parse_date_abbrev_month(nav_date_str)
    if as_of is None:
        return None

    investor_match = _NAVI_INVESTOR_NAME_RE.search(text)
    investor_name = investor_match.group(1).strip() if investor_match else None
    warnings: list[str] = []
    if investor_name is None:
        warnings.append("could not find an investor name")

    return {
        "document_type": "mutual_fund_cas",
        "doc_issued_at": doc_issued_at.isoformat(),
        "investor_name": investor_name,
        "source": "Navi Mutual Fund",
        "is_exhaustive": False,
        "holdings": [
            {
                "institution": "Navi Mutual Fund",
                "identifier": identifier,
                "instrument_name": _normalize_scheme_hyphens(scheme_name.strip()),
                "instrument_type": None,
                "units": units.replace(",", ""),
                "nav": nav.replace(",", ""),
                "value": current_value.replace(",", ""),
                "currency": "INR",
                "as_of": as_of.isoformat(),
            }
        ],
        "warnings": warnings,
    }
