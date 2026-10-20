import re
from datetime import date
from decimal import Decimal, InvalidOperation

AMOUNT_RE = re.compile(r"-?[\d,]+\.\d{2,4}")

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_NUMERIC_DATE_RE = re.compile(r"(\d{2})[/-](\d{2})[/-](\d{4})")
_ABBREV_MONTH_DATE_RE = re.compile(r"(\d{1,2})[\s-]([A-Za-z]{3})[\s-](\d{4})")
_MONTH_DAY_YEAR_RE = re.compile(r"([A-Za-z]{3})[a-z]*\s+(\d{1,2}),?\s+(\d{4})")


def find_all_amounts(text: str) -> list[Decimal]:
    amounts = []
    for match in AMOUNT_RE.finditer(text):
        try:
            amounts.append(Decimal(match.group(0).replace(",", "")))
        except InvalidOperation:
            continue
    return amounts


def parse_date_numeric(raw: str, day_first: bool) -> date | None:
    """DD/MM/YYYY or DD-MM-YYYY when day_first, MM/DD/YYYY or MM-DD-YYYY otherwise.

    Never guess between the two — the caller must know which format the issuing
    institution actually prints (confirmed per-parser against its own fixture),
    the same way the LLM system prompt is told explicitly rather than left to infer.
    """
    match = _NUMERIC_DATE_RE.search(raw)
    if not match:
        return None
    first, second, year = match.groups()
    day, month = (first, second) if day_first else (second, first)
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def parse_date_abbrev_month(raw: str) -> date | None:
    """'31-Jul-2026' or '31 Jul 2026' — day, three-letter month, year."""
    match = _ABBREV_MONTH_DATE_RE.search(raw)
    if not match:
        return None
    day, month_abbrev, year = match.groups()
    month = _MONTHS.get(month_abbrev.lower())
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def parse_date_month_day_year(raw: str) -> date | None:
    """'Jul 31, 2026' — three-letter month, day, year."""
    match = _MONTH_DAY_YEAR_RE.search(raw)
    if not match:
        return None
    month_abbrev, day, year = match.groups()
    month = _MONTHS.get(month_abbrev.lower())
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def find_line(lines: list[str], pattern: re.Pattern) -> tuple[int, str] | None:
    for index, line in enumerate(lines):
        if pattern.search(line):
            return index, line
    return None


def window(lines: list[str], index: int, size: int) -> list[str]:
    return lines[index : index + size]


def last_digits(raw: str, n: int = 4) -> str:
    digits = re.sub(r"\D", "", raw)
    return digits[-n:]
