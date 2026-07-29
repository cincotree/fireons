import re
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from statements.parsers.base import CASStatementParser, ParsedCASData, ParsedCASHolding
from statements.parsers.exceptions import UnrecognizedStatementFormatError
from statements.parsers.pdf_utils import decrypt_and_extract_text

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_NUMERIC_DATE_RE = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")
_TEXT_DATE_RE = re.compile(r"(\d{1,2})[-/]([A-Za-z]{3,9})[-/](\d{4})", re.IGNORECASE)

_AMC_LABEL_RE = re.compile(r"^\s*AMC\s*:\s*(.+?)\s*$", re.IGNORECASE)
_AMC_BARE_RE = re.compile(r"^\s*(.+?\bMutual Fund)\s*$", re.IGNORECASE)
_FOLIO_RE = re.compile(r"Folio\s*No\.?\s*:?\s*([\w/\-]+)", re.IGNORECASE)
_CAS_AS_ON_RE = re.compile(r"CAS\s+as\s+on\s*:?\s*(.+?)\s*$", re.IGNORECASE)
_ISIN_RE = re.compile(r"^\s*(?:ISIN\s*:?\s*)?([A-Z]{2}[A-Z0-9]{9}[0-9])\s*$")

_COMBINED_RE = re.compile(
    r"Closing\s*Balance\s*:?\s*([\d,]+\.\d+)\s*"
    r"NAV\s*:?\s*(?:Rs\.?)?\s*([\d,]+\.\d+).*?"
    r"Market\s*Value\s*:?\s*(?:Rs\.?)?\s*([\d,]+\.\d+)",
    re.IGNORECASE,
)
_CLOSING_UNIT_RE = re.compile(r"Closing\s*Unit\s*Balance\s*:?\s*([\d,]+\.\d+)", re.IGNORECASE)
_NAV_RE = re.compile(
    r"NAV(?:\s*as\s*on\s*(.+?))?\s*:?\s*(?:Rs\.?)?\s*([\d,]+\.\d+)", re.IGNORECASE
)
_MARKET_VALUE_RE = re.compile(r"Market\s*Value\s*:?\s*(?:Rs\.?)?\s*([\d,]+\.\d+)", re.IGNORECASE)
_DECIMAL_TOKEN_RE = re.compile(r"-?[\d,]+\.\d+")


def _parse_date(raw: str) -> Optional[date]:
    match = _NUMERIC_DATE_RE.search(raw)
    if match:
        day, month, year = match.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            return None

    match = _TEXT_DATE_RE.search(raw)
    if match:
        day, month_name, year = match.groups()
        month = _MONTHS.get(month_name[:3].lower())
        if month is None:
            return None
        try:
            return date(int(year), month, int(day))
        except ValueError:
            return None

    return None


def _is_boundary_line(line: str) -> bool:
    return bool(
        not line
        or _FOLIO_RE.search(line)
        or _AMC_LABEL_RE.match(line)
        or _AMC_BARE_RE.match(line)
        or _CAS_AS_ON_RE.search(line)
    )


def _to_decimal(raw: str) -> Optional[Decimal]:
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def _try_combined(line: str) -> Optional[tuple[Decimal, Decimal, Decimal, Optional[date]]]:
    match = _COMBINED_RE.search(line)
    if not match:
        return None
    units, nav, market_value = (_to_decimal(g) for g in match.groups())
    if units is None or nav is None or market_value is None:
        return None
    return units, nav, market_value, None


def _try_labeled_lines(
    lines: list[str],
) -> Optional[tuple[Decimal, Decimal, Decimal, Optional[date]]]:
    units: Optional[Decimal] = None
    nav: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    valuation_date: Optional[date] = None

    for line in lines:
        if units is None:
            match = _CLOSING_UNIT_RE.search(line)
            if match:
                units = _to_decimal(match.group(1))
                continue
        if nav is None:
            match = _NAV_RE.search(line)
            if match:
                nav = _to_decimal(match.group(2))
                if match.group(1):
                    valuation_date = _parse_date(match.group(1))
                continue
        if market_value is None:
            match = _MARKET_VALUE_RE.search(line)
            if match:
                market_value = _to_decimal(match.group(1))
                continue

    if units is None or nav is None or market_value is None:
        return None
    return units, nav, market_value, valuation_date


def _try_columnar(lines: list[str]) -> Optional[tuple[Decimal, Decimal, Decimal, Optional[date]]]:
    for line in lines:
        if "value" not in line.lower():
            continue
        tokens = _DECIMAL_TOKEN_RE.findall(line)
        if len(tokens) not in (2, 3):
            continue
        numbers = [_to_decimal(t) for t in tokens]
        if any(n is None for n in numbers):
            continue
        if len(numbers) == 3:
            units, nav, market_value = numbers
        else:
            units, market_value = numbers
            nav = market_value / units if units else Decimal("0")
        return units, nav, market_value, None
    return None


def _parse_summary(
    lines: list[str],
) -> Optional[tuple[Decimal, Decimal, Decimal, Optional[date]]]:
    for line in lines:
        result = _try_combined(line)
        if result:
            return result

    result = _try_labeled_lines(lines)
    if result:
        return result

    return _try_columnar(lines)


class CASParser(CASStatementParser):
    def parse(self, pdf_bytes: bytes, password: str) -> ParsedCASData:
        text = decrypt_and_extract_text(pdf_bytes, password)
        lines = [line.strip() for line in text.splitlines()]

        current_amc: Optional[str] = None
        current_folio: Optional[str] = None
        statement_date: Optional[date] = None
        warnings: list[str] = []
        pending: list[tuple[dict, Optional[date]]] = []

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            if not line:
                i += 1
                continue

            cas_date_match = _CAS_AS_ON_RE.search(line)
            if cas_date_match:
                statement_date = _parse_date(cas_date_match.group(1))
                i += 1
                continue

            amc_match = _AMC_LABEL_RE.match(line)
            if amc_match:
                current_amc = amc_match.group(1)
                i += 1
                continue
            amc_match = _AMC_BARE_RE.match(line)
            if amc_match:
                current_amc = amc_match.group(1)
                i += 1
                continue

            folio_match = _FOLIO_RE.search(line)
            if folio_match:
                current_folio = folio_match.group(1)
                i += 1
                continue

            if current_amc is None or current_folio is None:
                i += 1
                continue

            # A scheme block runs from here up to the next recognized
            # boundary line (a new Folio No/AMC/CAS-as-on line, or a blank
            # line) — pypdf's extracted text doesn't reliably keep blank
            # lines between scheme entries, so boundary lines are the only
            # dependable separator until this is checked against a real
            # CAS PDF (see the parser's real-sample validation gate).
            block_end = i + 1
            while block_end < n and not _is_boundary_line(lines[block_end]):
                block_end += 1
            block = lines[i:block_end]
            i = block_end

            scheme_name = block[0]
            remaining = block[1:]

            isin: Optional[str] = None
            if remaining:
                isin_match = _ISIN_RE.match(remaining[0])
                if isin_match:
                    isin = isin_match.group(1)
                    remaining = remaining[1:]

            summary = _parse_summary(remaining)
            if summary is None:
                warnings.append(
                    f"Could not parse balance for scheme '{scheme_name}' "
                    f"(folio {current_folio}) — skipped."
                )
                continue

            units, nav, market_value, local_date = summary
            pending.append(
                (
                    {
                        "amc": current_amc,
                        "scheme_name": scheme_name,
                        "folio_number": current_folio,
                        "isin": isin,
                        "units": units,
                        "nav": nav,
                        "market_value": market_value,
                        "source": None,
                    },
                    local_date,
                )
            )

        if not pending:
            raise UnrecognizedStatementFormatError(
                "This PDF doesn't look like a CAS statement we recognize "
                "(no folios or scheme holdings found)."
            )

        if statement_date is None:
            local_dates = [d for _, d in pending if d is not None]
            if local_dates:
                statement_date = Counter(local_dates).most_common(1)[0][0]
            else:
                statement_date = date.today()
                warnings.append(
                    "Could not detect the CAS statement date — defaulted to today. "
                    "Please verify it below."
                )

        holdings = [
            ParsedCASHolding(valuation_date=local_date or statement_date, **kwargs)
            for kwargs, local_date in pending
        ]

        return ParsedCASData(statement_date=statement_date, holdings=holdings, warnings=warnings)
