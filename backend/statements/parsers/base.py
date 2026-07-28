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
