import re
from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_api import get_current_user
from database.models import User
from database.repository import AccountRepository, BalanceRepository
from database.session import get_session
from statements.parsers import get_cas_parser
from statements.parsers.exceptions import (
    IncorrectPasswordError,
    InvalidPDFError,
    StatementParseError,
    UnrecognizedStatementFormatError,
)

router = APIRouter(prefix="/statements/cas", tags=["cas-statements"])

MAX_CAS_STATEMENT_SIZE_BYTES = 15 * 1024 * 1024

_WHITESPACE_RE = re.compile(r"\s+")


def _sanitize_component(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip()).replace(":", "-")


def _suggested_account_name(amc: str, folio_number: str, scheme_name: str) -> str:
    return (
        f"Assets:Investment:MutualFund:{_sanitize_component(amc)}:"
        f"{_sanitize_component(folio_number)}:{_sanitize_component(scheme_name)}"
    )


class CASHoldingPreview(BaseModel):
    amc: str
    scheme_name: str
    folio_number: str
    isin: Optional[str]
    units: Decimal
    nav: Decimal
    market_value: Decimal
    valuation_date: date_type
    source: Optional[str]
    suggested_account_name: str
    existing_account_id: Optional[str]
    warnings: list[str]


class CASParseResponse(BaseModel):
    statement_date: date_type
    holdings: list[CASHoldingPreview]
    warnings: list[str]


class CASHoldingConfirm(BaseModel):
    amc: str
    scheme_name: str
    folio_number: str
    isin: Optional[str] = None
    units: Decimal
    nav: Decimal
    market_value: Decimal
    valuation_date: date_type
    account_name: str
    currency: str = "INR"
    source: Optional[str] = None


class CASConfirmRequest(BaseModel):
    holdings: list[CASHoldingConfirm]


class CASHoldingResult(BaseModel):
    account_id: str
    account_name: str
    balance_id: str
    amount: Decimal
    currency: str
    date: date_type
    was_created: bool


class CASConfirmResponse(BaseModel):
    results: list[CASHoldingResult]
    created_count: int
    updated_count: int


@router.post("/parse", response_model=CASParseResponse)
async def parse_cas_statement(
    file: UploadFile = File(...),
    password: str = Form(...),
    source: str = Form("Unknown"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    content = await file.read()
    if len(content) > MAX_CAS_STATEMENT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Statement file is too large")

    parser = get_cas_parser()
    try:
        parsed = parser.parse(content, password)
    except IncorrectPasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except UnrecognizedStatementFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except InvalidPDFError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except StatementParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    account_repo = AccountRepository(session)
    previews = []
    for holding in parsed.holdings:
        suggested_account_name = _suggested_account_name(
            holding.amc, holding.folio_number, holding.scheme_name
        )
        existing_account = await account_repo.get_by_name(
            suggested_account_name, current_user.id
        )
        previews.append(
            CASHoldingPreview(
                amc=holding.amc,
                scheme_name=holding.scheme_name,
                folio_number=holding.folio_number,
                isin=holding.isin,
                units=holding.units,
                nav=holding.nav,
                market_value=holding.market_value,
                valuation_date=holding.valuation_date,
                source=source,
                suggested_account_name=suggested_account_name,
                existing_account_id=existing_account.id if existing_account else None,
                warnings=holding.warnings,
            )
        )

    return CASParseResponse(
        statement_date=parsed.statement_date,
        holdings=previews,
        warnings=parsed.warnings,
    )


@router.post("/confirm", response_model=CASConfirmResponse)
async def confirm_cas_statement(
    confirm_data: CASConfirmRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not confirm_data.holdings:
        raise HTTPException(status_code=400, detail="No holdings were submitted")

    for holding in confirm_data.holdings:
        first_component = holding.account_name.split(":")[0]
        if first_component != "Assets":
            raise HTTPException(
                status_code=400,
                detail=f"Account name must start with 'Assets:' (got '{holding.account_name}')",
            )

    account_repo = AccountRepository(session)
    balance_repo = BalanceRepository(session)

    results = []
    created_count = 0
    updated_count = 0

    for holding in confirm_data.holdings:
        meta = {
            "amc": holding.amc,
            "folio_number": holding.folio_number,
            "isin": holding.isin,
            "units": str(holding.units),
            "nav": str(holding.nav),
            "source": holding.source,
        }

        account = await account_repo.get_by_name(holding.account_name, current_user.id)
        if account is None:
            account = await account_repo.create(
                user_id=current_user.id,
                name=holding.account_name,
                open_date=holding.valuation_date,
                currency=holding.currency,
                meta=meta,
            )
            was_created = True
            created_count += 1
        else:
            account = await account_repo.update(account.id, meta=meta)
            was_created = False
            updated_count += 1

        balance = await balance_repo.create_or_update(
            account_id=account.id,
            date=holding.valuation_date,
            amount=holding.market_value,
            currency=holding.currency,
        )

        results.append(
            CASHoldingResult(
                account_id=account.id,
                account_name=account.name,
                balance_id=balance.id,
                amount=balance.amount,
                currency=balance.currency,
                date=balance.date,
                was_created=was_created,
            )
        )

    await session.commit()

    return CASConfirmResponse(
        results=results,
        created_count=created_count,
        updated_count=updated_count,
    )
