from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import ClassVar, Optional

from pydantic import BaseModel


class ParsedStatementData(BaseModel):
    bank: str
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    account_number_last4: Optional[str] = None
    currency: str
    closing_balance: Decimal
    statement_date: date
    warnings: list[str] = []


class BankStatementParser(ABC):
    bank_code: ClassVar[str]

    @abstractmethod
    def parse(self, pdf_bytes: bytes, password: str) -> ParsedStatementData:
        """Decrypt and parse a bank statement PDF into ParsedStatementData.

        Raises IncorrectPasswordError, InvalidPDFError, or
        UnrecognizedStatementFormatError from statements.parsers.exceptions.
        """
        raise NotImplementedError


class ParsedCASHolding(BaseModel):
    amc: str
    scheme_name: str
    folio_number: str
    isin: Optional[str] = None
    units: Decimal
    nav: Decimal
    market_value: Decimal
    valuation_date: date
    source: Optional[str] = None
    warnings: list[str] = []


class ParsedCASData(BaseModel):
    statement_date: date
    holdings: list[ParsedCASHolding]
    warnings: list[str] = []


class CASStatementParser(ABC):
    @abstractmethod
    def parse(self, pdf_bytes: bytes, password: str) -> ParsedCASData:
        """Decrypt and parse a mutual fund CAS PDF into ParsedCASData.

        Raises IncorrectPasswordError, InvalidPDFError, or
        UnrecognizedStatementFormatError from statements.parsers.exceptions.
        """
        raise NotImplementedError
