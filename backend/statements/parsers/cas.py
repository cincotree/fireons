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

# A holding's first line: folio number (plain digits, or "digits/digits" for
# sub-accounts), then its market value (always 2 decimals, a currency
# amount), then the scheme code + name glued on with no separating
# whitespace (a text-extraction artifact of adjacent PDF table cells).
_HOLDING_START_RE = re.compile(r"^(\d+(?:/\d+)?)\s+([\d,]+\.\d{2})(\D.*)$")

# A holding's closing line: unit balance, NAV date, NAV, then the registrar
# name glued directly onto the ISIN (e.g. "CAMSINF209K01108",
# "KFINTECHINF846K01131"), then cost value. Units/NAV/cost value have a
# variable number of decimals; only the market value above is fixed at 2.
_HOLDING_DETAIL_RE = re.compile(
    r"^([\d,]+\.\d+)\s+"
    r"(\d{1,2}-[A-Za-z]{3,9}-\d{4})\s+"
    r"([\d,]+\.\d+)\s+"
    r"(\S*?(INF[0-9A-Z]{9}))\s+"
    r"([\d,]+\.\d+)\s*$"
)

_STATEMENT_DATE_RE = re.compile(r"^\s*As\s+on\s*:?\s*(.+?)\s*$", re.IGNORECASE)

# Known SEBI-registered AMC name prefixes, as they appear in scheme text
# (without the "Mutual Fund" suffix), mapped to a canonical display name so
# variants (different sub-brands, or casing like "BARODA BNP PARIBAS" vs
# "Baroda BNP Paribas") all group under one AMC. Matched case-insensitively,
# longest prefix first, so a more specific prefix (e.g. "Aditya Birla Sun
# Life") wins over a shorter one that happens to also match.
_AMC_ALIASES: list[tuple[str, str]] = [
    ("Aditya Birla Sun Life", "Aditya Birla Sun Life"),
    ("Bajaj Finserv", "Bajaj Finserv"),
    ("Bandhan", "Bandhan"),
    ("Bank of India", "Bank of India"),
    ("Baroda BNP Paribas", "Baroda BNP Paribas"),
    ("Canara Robeco", "Canara Robeco"),
    ("DSP", "DSP"),
    ("Edelweiss", "Edelweiss"),
    ("Franklin Templeton", "Franklin Templeton"),
    ("Franklin India", "Franklin Templeton"),
    ("Franklin", "Franklin Templeton"),
    ("Groww", "Groww"),
    ("HDFC", "HDFC"),
    ("HSBC", "HSBC"),
    ("Helios", "Helios"),
    ("ICICI Prudential", "ICICI Prudential"),
    ("IDBI", "IDBI"),
    ("IIFL", "IIFL"),
    ("ITI", "ITI"),
    ("Invesco India", "Invesco"),
    ("Invesco", "Invesco"),
    ("JM Financial", "JM Financial"),
    ("JM", "JM Financial"),
    ("Kotak Mahindra", "Kotak Mahindra"),
    ("Kotak", "Kotak Mahindra"),
    ("LIC", "LIC"),
    ("Mahindra Manulife", "Mahindra Manulife"),
    ("Mirae Asset", "Mirae Asset"),
    ("Motilal Oswal", "Motilal Oswal"),
    ("Navi", "Navi"),
    ("Nippon India", "Nippon India"),
    ("NJ", "NJ"),
    ("Old Bridge", "Old Bridge"),
    ("PGIM India", "PGIM India"),
    ("Parag Parikh", "PPFAS (Parag Parikh)"),
    ("PPFAS", "PPFAS (Parag Parikh)"),
    ("Quantum", "Quantum"),
    ("Quant", "Quant"),
    ("SBI", "SBI"),
    ("Samco", "Samco"),
    ("Shriram", "Shriram"),
    ("Sundaram", "Sundaram"),
    ("Tata", "Tata"),
    ("Taurus", "Taurus"),
    ("Trust", "Trust"),
    ("UTI", "UTI"),
    ("Union", "Union"),
    ("WhiteOak Capital", "WhiteOak Capital"),
    ("Zerodha", "Zerodha"),
    ("360 ONE", "360 ONE"),
    ("Axis", "Axis"),
]
_AMC_ALIASES_BY_LENGTH = sorted(_AMC_ALIASES, key=lambda pair: len(pair[0]), reverse=True)


def _parse_date(raw: str) -> Optional[date]:
    match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
    if match:
        day, month, year = match.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            return None

    match = re.search(r"(\d{1,2})[-/]([A-Za-z]{3,9})[-/](\d{4})", raw)
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


def _to_decimal(raw: str) -> Optional[Decimal]:
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def _split_registrar_isin(token: str) -> tuple[Optional[str], Optional[str]]:
    match = re.search(r"INF[0-9A-Z]{9}", token)
    if not match:
        return None, None
    isin = match.group(0)
    registrar = token[: match.start()].strip() or None
    return registrar, isin


def _split_amc_and_scheme(raw_scheme_text: str) -> tuple[str, str, list[str]]:
    """Split "<code> - <AMC name><scheme descriptor>" into (amc, scheme_name, warnings).

    scheme_name keeps the leading scheme code (useful to disambiguate very
    similar plans) but drops the AMC name, since the account naming
    convention already puts AMC in its own path segment.
    """
    warnings: list[str] = []
    text = re.sub(r"\s+", " ", raw_scheme_text).strip()

    if " - " in text:
        code, descriptor = text.split(" - ", 1)
    else:
        code, descriptor = "", text
    code = code.strip()
    descriptor = descriptor.strip()

    amc: Optional[str] = None
    remainder = descriptor
    for prefix, canonical in _AMC_ALIASES_BY_LENGTH:
        if descriptor.lower().startswith(prefix.lower()):
            amc = canonical
            remainder = descriptor[len(prefix):].strip(" -")
            break

    if amc is None:
        words = descriptor.split(" ")
        amc = " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else "Unknown")
        remainder = " ".join(words[2:]).strip(" -") if len(words) > 2 else descriptor
        warnings.append(
            f"Could not confidently identify the AMC for '{descriptor}' "
            f"— guessed '{amc}', please verify."
        )

    scheme_name = f"{code} - {remainder}" if code and remainder else (remainder or code or descriptor)
    return amc, scheme_name, warnings


class CASParser(CASStatementParser):
    def parse(self, pdf_bytes: bytes, password: str) -> ParsedCASData:
        text = decrypt_and_extract_text(pdf_bytes, password)
        lines = [line.strip() for line in text.splitlines()]

        statement_date: Optional[date] = None
        warnings: list[str] = []
        pending: list[tuple[dict, Optional[date]]] = []

        pending_start: Optional[re.Match] = None
        scheme_text_lines: list[str] = []

        for line in lines:
            if not line:
                continue

            if statement_date is None:
                date_match = _STATEMENT_DATE_RE.match(line)
                if date_match:
                    statement_date = _parse_date(date_match.group(1))
                    continue

            start_match = _HOLDING_START_RE.match(line)
            if start_match:
                # A new holding started before the previous one's detail
                # line was found (shouldn't normally happen) — drop the
                # incomplete one rather than silently merging it into this
                # one's data.
                if pending_start is not None:
                    warnings.append(
                        "Could not find balance details for a scheme before the "
                        "next one started — skipped."
                    )
                pending_start = start_match
                scheme_text_lines = [start_match.group(3)]
                continue

            if pending_start is None:
                continue

            detail_match = _HOLDING_DETAIL_RE.match(line)
            if not detail_match:
                scheme_text_lines.append(line)
                continue

            folio_number = pending_start.group(1)
            market_value = _to_decimal(pending_start.group(2))
            raw_scheme_text = " ".join(scheme_text_lines)
            amc, scheme_name, split_warnings = _split_amc_and_scheme(raw_scheme_text)

            units = _to_decimal(detail_match.group(1))
            local_date = _parse_date(detail_match.group(2))
            nav = _to_decimal(detail_match.group(3))
            registrar, isin = _split_registrar_isin(detail_match.group(4))
            cost_value = _to_decimal(detail_match.group(6))

            pending_start = None
            scheme_text_lines = []

            if market_value is None or units is None or nav is None or cost_value is None:
                warnings.append(
                    f"Could not parse balance for scheme '{scheme_name}' "
                    f"(folio {folio_number}) — skipped."
                )
                continue

            pending.append(
                (
                    {
                        "amc": amc,
                        "scheme_name": scheme_name,
                        "folio_number": folio_number,
                        "isin": isin,
                        "units": units,
                        "nav": nav,
                        "market_value": market_value,
                        "source": registrar,
                        "warnings": split_warnings,
                    },
                    local_date,
                )
            )

        if pending_start is not None:
            warnings.append(
                f"Could not find balance details for the scheme starting at "
                f"folio {pending_start.group(1)} — skipped."
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
