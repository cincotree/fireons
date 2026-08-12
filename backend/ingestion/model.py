from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class Position(BaseModel):
    account_name: str
    value: str
    currency: str
    as_of: date
    units: str | None = None
    nav: str | None = None
    doc_issued_at: datetime | None = None
    source: str | None = None

    @field_validator("value", "units", "nav")
    @classmethod
    def _parses_as_decimal(cls, v: str | None) -> str | None:
        if v is not None:
            Decimal(v)
        return v


class NetWorth(BaseModel):
    as_of: date | None
    reporting_currency: str
    positions: dict[str, Position]
    total: str
    warnings: list[str] = []

    @field_validator("total")
    @classmethod
    def _parses_as_decimal(cls, v: str) -> str:
        Decimal(v)
        return v
