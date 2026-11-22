import re

from ingestion.parsers._text_utils import parse_date_abbrev_month, parse_date_numeric

_SECTION_INSTRUMENT_TYPES = {
    "EQUITY HOLDINGS": "equity",
    "REIT HOLDINGS": "reit",
    "INVIT HOLDINGS": "invit",
    "ETF HOLDINGS": "etf",
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


# CDSL's own "Consolidated Account Statement" (as opposed to the NSDL/CDSL joint
# statement above) is a much bigger, messier document: trilingual boilerplate
# repeated at every page break, one "HOLDING STATEMENT AS ON <date>" table per
# depository account (CDSL-registered ones printed compactly on one data line
# per ISIN; NSDL-registered ones printed with one value per line instead), a
# separate lock-in-schedule table confusingly also titled "HOLDING STATEMENT ...
# (Other Details)" that must NOT be scanned, and non-equity ISINs mixed directly
# into the same table: mutual fund units and bonds/NCDs held in demat form,
# neither of which demat_cas's instrument_type schema (equity/reit/invit) can
# represent — those are skipped with a warning rather than guessed at.
_CDSL_HOLDING_STATEMENT_DATE_RE = re.compile(r"HOLDING STATEMENT AS ON\s*(\d{2}-\d{2}-\d{4})")
_CDSL_SECTION_BOUNDARY_RE = re.compile(
    r"STATEMENT OF TRANSACTIONS FOR THE PERIOD|HOLDING STATEMENT AS ON"
)
# A per-ISIN block runs until the next ISIN, the next table/page's repeated
# column-header block, or a page boundary — whichever comes first. Without this,
# the last ISIN in a section absorbs everything up to the next section boundary,
# including unrelated numbers from the trilingual header repeat and the next
# section's own total.
_CDSL_INNER_BOUNDARY_RE = re.compile(
    r"ISINISIN|Page \d+ of \d+|CONSOLIDATED ACCOUNT STATEMENT|STATEMENT OF TRANSACTIONS"
)
_ISIN_TOKEN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")
# "FACE VALUE RS. 2/-" / "RE.1/-" prints a bare denomination number inline with
# the security description — indistinguishable from a real balance/price column
# by shape alone, so it's stripped before the remaining numbers are read
# positionally (units, price, value from the end).
_FACE_VALUE_NUM_RE = re.compile(r"[\d.]+\s*/-")
_HOLDING_NUM_RE = re.compile(r"[\d,]*\d\.\d+|\b\d+\b")
_FUND_OR_BOND_MARKER_RE = re.compile(r"MF-|\bNCD\b|\bDEBENTURE\b")
# The security's legal name always precedes a share-type descriptor, but that
# descriptor is glued on with any of several separators depending on the
# document — "LIMITED # EQUITY SHARES", "LIMITED#NEW EQUITY SHARES",
# "LTD- NEW RE 1-AFTER SPLIT", "LIMITED - EQUITY SHARES", or no separator at
# all ("LIMITED EQUITY SHARES"). Rather than enumerate every separator, the
# name is taken up through its own legal-entity suffix instead — "LIMITED" or
# "LTD" for a company, "TRUST" for a REIT/InvIT — which is present in every
# real holding seen and is a much more stable anchor than whatever glue text
# happens to follow it.
_SECURITY_NAME_CUTOFF_RE = re.compile(r"\b(?:LIMITED|LTD|TRUST)\b")
# Strips the trailing "<units> -- -- -- <free_bal> <price> <value>" numeric
# row off the end of an ETF's product name (which, unlike a company name, has
# no LIMITED/LTD/TRUST suffix to cut on) — a run of 2+ dash/decimal tokens
# anchored at the end of the block text.
_TRAILING_NUMERIC_ROW_RE = re.compile(r"(?:\s+(?:--|[\d,]+\.\d+)){2,}\s*$")


def try_parse_cdsl_consolidated_demat_cas(text: str) -> dict | None:
    if "Central Depository Services" not in text or "HOLDING STATEMENT AS ON" not in text:
        return None

    date_match = _CDSL_HOLDING_STATEMENT_DATE_RE.search(text)
    if date_match is None:
        return None
    as_of = parse_date_numeric(date_match.group(1), day_first=True)
    if as_of is None:
        return None

    section_starts = []
    for match in re.finditer(r"HOLDING STATEMENT AS ON", text):
        if "(Other Details)" in text[match.start() : match.start() + 80]:
            continue
        section_starts.append(match.start())
    if not section_starts:
        return None

    windows = []
    for start in section_starts:
        boundary = _CDSL_SECTION_BOUNDARY_RE.search(text, start + 30)
        windows.append((start, boundary.start() if boundary else len(text)))

    seen_isins: set[str] = set()
    holdings = []
    warnings: list[str] = []

    for start, end in windows:
        window_text = text[start:end]
        isin_matches = list(_ISIN_TOKEN_RE.finditer(window_text))
        for index, isin_match in enumerate(isin_matches):
            isin = isin_match.group(0)
            if isin in seen_isins:
                continue

            block_start = isin_match.end()
            next_isin_start = (
                isin_matches[index + 1].start()
                if index + 1 < len(isin_matches)
                else len(window_text)
            )
            raw_block = window_text[block_start:next_isin_start]
            inner_boundary = _CDSL_INNER_BOUNDARY_RE.search(raw_block)
            block = raw_block[: inner_boundary.start()] if inner_boundary else raw_block

            cleaned = _FACE_VALUE_NUM_RE.sub("", block)
            nums = [n.replace(",", "") for n in _HOLDING_NUM_RE.findall(cleaned)]
            if len(nums) < 3 or not re.match(r"^\d+\.\d{2}$", nums[-1]):
                continue

            normalized_block = re.sub(r"\s+", " ", block).strip()
            desc = normalized_block.upper()
            name_cutoff = _SECURITY_NAME_CUTOFF_RE.search(normalized_block)
            instrument_name = normalized_block[: name_cutoff.end()].strip() if name_cutoff else None
            if "REIT" in desc:
                instrument_type = "reit"
            elif "INVIT" in desc:
                instrument_type = "invit"
            elif "ETF" in desc:
                # An ETF's description is printed exactly like a demat-held
                # mutual fund's ("NIPPON LIFE INDIA AM LTD#NIPPON INDIA
                # MF-NIPPON INDIA ETF GOLD BEES" — same "MF-" naming
                # convention as an open-ended fund) but it trades on the
                # exchange via its own ISIN just like a stock, not through a
                # folio. Checked before the MF-/NCD exclusion below — real
                # documents confirmed multiple ETF holdings (Gold BEES, Nifty
                # 50 BEES, Nifty Next 50 BEES) worth several lakh rupees
                # combined were silently excluded entirely because their
                # AMC-name text also contains "MF-". Its own instrument_type
                # ("etf" -> Assets:Investment:ETF:...) rather than lumping it
                # under equity — buried among two dozen ordinary stocks, the
                # user couldn't find these at all in the account tree.
                instrument_type = "etf"
                # The LIMITED/LTD cutoff above grabs the fund HOUSE's own name
                # ("Nippon Life India Am Ltd"), which precedes the actual
                # product name here — the real ETF name comes after "MF-"
                # instead ("Nippon India Etf Gold Bees").
                mf_dash_index = desc.find("MF-")
                if mf_dash_index != -1:
                    after_mf = normalized_block[mf_dash_index + len("MF-") :].strip()
                    trailing_numbers = _TRAILING_NUMERIC_ROW_RE.search(after_mf)
                    if trailing_numbers:
                        after_mf = after_mf[: trailing_numbers.start()].strip()
                    if after_mf:
                        instrument_name = after_mf
            elif _FUND_OR_BOND_MARKER_RE.search(desc):
                seen_isins.add(isin)
                warnings.append(
                    f"{isin}: mutual fund units or bonds held in demat form are not captured"
                )
                continue
            else:
                instrument_type = "equity"

            units, price, value = nums[-3], nums[-2], nums[-1]
            seen_isins.add(isin)
            holdings.append(
                {
                    "institution": None,
                    "identifier": isin,
                    "instrument_name": instrument_name,
                    "instrument_type": instrument_type,
                    "units": units,
                    "nav": price,
                    "value": value,
                    "currency": "INR",
                    "as_of": as_of.isoformat(),
                }
            )

    if not holdings:
        return None

    return {
        "document_type": "demat_cas",
        "doc_issued_at": as_of.isoformat(),
        "investor_name": None,
        "source": "CDSL",
        "is_exhaustive": True,
        "holdings": holdings,
        "warnings": warnings,
    }
