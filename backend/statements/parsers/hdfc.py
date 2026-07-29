import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import ClassVar, Optional

from statements.parsers.base import BankStatementParser, ParsedStatementData
from statements.parsers.exceptions import UnrecognizedStatementFormatError
from statements.parsers.pdf_utils import decrypt_and_extract_text

_ACCOUNT_NO_RE = re.compile(r"account\s*no\.?\s*:?\s*(\d{9,18})", re.IGNORECASE)
_NAME_LABEL_RE = re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.IGNORECASE)
# Real HDFC statements print the holder's name as a bare line with a
# courtesy title and no "Name:" label at all, e.g. "MR. JOHN SMITH".
_NAME_TITLE_RE = re.compile(
    r"^\s*(?:MR|MRS|MS|MISS|M/S|DR|SHRI|SMT|KUM)\.?\s+\S.*", re.IGNORECASE
)
# Matches both an inline "Closing Balance as on ..." line and the
# "STATEMENT SUMMARY" table's abbreviated "Closing Bal" column header.
_CLOSING_BALANCE_LABEL_RE = re.compile(r"closing\s*bal", re.IGNORECASE)
_TO_DATE_RE = re.compile(r"\bto\s*:?\s*(\d{2}[/-]\d{2}[/-]\d{4})", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"-?[\d,]+\.\d{2}")
_DATE_RE = re.compile(r"(\d{2})[/-](\d{2})[/-](\d{4})")

# How many lines after a "Closing Balance" label to search for the amount,
# in case text extraction puts the label and value on separate lines.
_CLOSING_BALANCE_WINDOW = 3


def _parse_date(raw: str) -> Optional[date]:
    match = _DATE_RE.search(raw)
    if not match:
        return None
    day, month, year = match.groups()
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def _find_all_amounts(raw: str) -> list[Decimal]:
    amounts = []
    for match in _AMOUNT_RE.finditer(raw):
        try:
            amounts.append(Decimal(match.group(0).replace(",", "")))
        except InvalidOperation:
            continue
    return amounts


def _find_account_number(lines: list[str]) -> Optional[str]:
    for line in lines:
        match = _ACCOUNT_NO_RE.search(line)
        if match:
            return match.group(1)
    return None


def _find_account_holder_name(lines: list[str]) -> Optional[str]:
    for line in lines:
        match = _NAME_LABEL_RE.match(line)
        if match:
            name = match.group(1).strip()
            if name:
                return name

    for line in lines:
        match = _NAME_TITLE_RE.match(line)
        if match:
            name = line.strip()
            if name:
                return name

    return None


def _find_closing_balance(lines: list[str]) -> tuple[Optional[Decimal], Optional[date]]:
    for index, line in enumerate(lines):
        if not _CLOSING_BALANCE_LABEL_RE.search(line):
            continue

        window = lines[index : index + _CLOSING_BALANCE_WINDOW]
        amounts: list[Decimal] = []
        stmt_date: Optional[date] = None
        for window_line in window:
            amounts.extend(_find_all_amounts(window_line))
            if stmt_date is None:
                stmt_date = _parse_date(window_line)
        if amounts:
            # The closing balance is the last amount in the window: for an
            # inline "Closing Balance as on ... : X" line it's the only
            # amount; for a "STATEMENT SUMMARY" table (Opening Balance, Dr
            # Count, Cr Count, Debits, Credits, Closing Bal) it's the
            # rightmost column.
            return amounts[-1], stmt_date

    return None, None


def _find_statement_period_end(lines: list[str]) -> Optional[date]:
    for line in lines:
        match = _TO_DATE_RE.search(line)
        if match:
            return _parse_date(match.group(1))
    return None


class HDFCStatementParser(BankStatementParser):
    bank_code: ClassVar[str] = "HDFC"
    currency: ClassVar[str] = "INR"

    def parse(self, pdf_bytes: bytes, password: str) -> ParsedStatementData:
        text = decrypt_and_extract_text(pdf_bytes, password)
        lines = text.splitlines()

        account_number = _find_account_number(lines)
        closing_balance, closing_balance_date = _find_closing_balance(lines)

        if account_number is None and closing_balance is None:
            raise UnrecognizedStatementFormatError(
                "This PDF doesn't look like an HDFC Bank statement "
                "(no account number or closing balance found)."
            )

        warnings: list[str] = []

        account_holder_name = _find_account_holder_name(lines)
        if account_holder_name is None:
            warnings.append("Could not detect the account holder name — please verify it below.")

        if closing_balance is None:
            raise UnrecognizedStatementFormatError(
                "Could not find a closing balance in this statement."
            )

        statement_date = closing_balance_date
        if statement_date is None:
            statement_date = _find_statement_period_end(lines)
        if statement_date is None:
            statement_date = date.today()
            warnings.append(
                "Could not detect the statement date — defaulted to today. Please verify it below."
            )

        account_number_last4 = account_number[-4:] if account_number else None
        if account_number is None:
            warnings.append("Could not detect the account number — please enter it below.")

        return ParsedStatementData(
            bank=self.bank_code,
            account_holder_name=account_holder_name,
            account_number=account_number,
            account_number_last4=account_number_last4,
            currency=self.currency,
            closing_balance=closing_balance,
            statement_date=statement_date,
            warnings=warnings,
        )
