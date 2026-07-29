from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession

from api.account_api import BalanceResponse
from api.auth_api import get_current_user
from database.models import User
from database.repository import AccountRepository, BalanceRepository
from database.session import get_session
from statements.parsers import get_parser, list_supported_banks
from statements.parsers.exceptions import (
    IncorrectPasswordError,
    InvalidPDFError,
    StatementParseError,
    UnrecognizedStatementFormatError,
    UnsupportedBankError,
)

router = APIRouter(prefix="", tags=["statements"])

MAX_STATEMENT_SIZE_BYTES = 15 * 1024 * 1024


class StatementParseResponse(BaseModel):
    bank: str
    account_holder_name: Optional[str]
    account_number: Optional[str]
    account_number_last4: Optional[str]
    currency: str
    closing_balance: Decimal
    statement_date: date_type
    suggested_account_name: str
    warnings: list[str]


class StatementConfirmRequest(BaseModel):
    bank: str
    account_name: str
    currency: str
    closing_balance: Decimal
    statement_date: date_type
    account_number: Optional[str] = None
    account_holder_name: Optional[str] = None
    description: Optional[str] = None


def _suggested_account_name(bank: str, account_number_last4: Optional[str]) -> str:
    if account_number_last4:
        return f"Assets:Bank:{bank}:{account_number_last4}"
    return f"Assets:Bank:{bank}"


@router.get("/statements/banks", response_model=list[str])
async def get_supported_banks(current_user: User = Depends(get_current_user)):
    return list_supported_banks()


@router.post("/statements/parse", response_model=StatementParseResponse)
async def parse_statement(
    file: UploadFile = File(...),
    password: str = Form(...),
    bank: str = Form("HDFC"),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > MAX_STATEMENT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Statement file is too large")

    try:
        parser = get_parser(bank)
    except UnsupportedBankError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

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

    return StatementParseResponse(
        bank=parsed.bank,
        account_holder_name=parsed.account_holder_name,
        account_number=parsed.account_number,
        account_number_last4=parsed.account_number_last4,
        currency=parsed.currency,
        closing_balance=parsed.closing_balance,
        statement_date=parsed.statement_date,
        suggested_account_name=_suggested_account_name(parsed.bank, parsed.account_number_last4),
        warnings=parsed.warnings,
    )


@router.post("/statements/confirm", response_model=BalanceResponse)
async def confirm_statement(
    confirm_data: StatementConfirmRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    first_component = confirm_data.account_name.split(":")[0]
    if first_component not in ["Assets", "Liabilities"]:
        raise HTTPException(
            status_code=400,
            detail="Account name must start with 'Assets:' or 'Liabilities:'",
        )

    account_repo = AccountRepository(session)
    balance_repo = BalanceRepository(session)

    try:
        account = await account_repo.create(
            user_id=current_user.id,
            name=confirm_data.account_name,
            open_date=confirm_data.statement_date,
            currency=confirm_data.currency,
            description=confirm_data.description,
            meta={
                "bank": confirm_data.bank,
                "account_number": confirm_data.account_number,
                "account_holder_name": confirm_data.account_holder_name,
                "source": "statement_upload",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    balance = await balance_repo.create_or_update(
        account_id=account.id,
        date=confirm_data.statement_date,
        amount=confirm_data.closing_balance,
        currency=confirm_data.currency,
    )
    await session.commit()

    return BalanceResponse(
        id=balance.id,
        account_id=account.id,
        account_name=account.name,
        account_type=account.account_type.value,
        amount=balance.amount,
        currency=balance.currency,
        date=balance.date,
    )
