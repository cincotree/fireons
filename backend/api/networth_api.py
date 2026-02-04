from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from database.session import get_session
from database.models import AccountType, User
from database.repository import AccountRepository, BalanceRepository, ExchangeRateRepository
from api.auth_api import get_current_user

router = APIRouter(prefix="/networth", tags=["networth"])


class AccountCreate(BaseModel):
    name: str
    currency: str = "USD"
    description: Optional[str] = None
    open_date: date_type = Field(default_factory=date_type.today)


class AccountResponse(BaseModel):
    id: str
    name: str
    account_type: str
    currency: str
    description: Optional[str]
    open_date: date_type
    close_date: Optional[date_type]
    is_active: bool
    balance: Optional[Decimal] = None
    balance_in_display_currency: Optional[Decimal] = None
    display_currency: Optional[str] = None

    class Config:
        from_attributes = True


class BalanceCreate(BaseModel):
    account_id: str
    amount: Decimal
    currency: str
    date: date_type = Field(default_factory=date_type.today)


class BalanceResponse(BaseModel):
    id: str
    account_id: str
    account_name: str
    account_type: str
    amount: Decimal
    currency: str
    date: date_type

    class Config:
        from_attributes = True


class NetWorthSummary(BaseModel):
    currency: str
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal


class NetWorthResponse(BaseModel):
    as_of_date: date_type
    by_currency: list[NetWorthSummary]
    entries: list[BalanceResponse]


class ExchangeRateCreate(BaseModel):
    from_currency: str
    to_currency: str
    rate: Decimal
    date: date_type = Field(default_factory=date_type.today)
    source: Optional[str] = None


class ExchangeRateResponse(BaseModel):
    id: str
    from_currency: str
    to_currency: str
    rate: Decimal
    date: date_type
    source: Optional[str]

    class Config:
        from_attributes = True


@router.get("/accounts", response_model=list[AccountResponse])
async def list_networth_accounts(
    display_currency: str = "USD",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)
    balance_repo = BalanceRepository(session)
    rate_repo = ExchangeRateRepository(session)

    accounts = []
    for account_type in [AccountType.ASSETS, AccountType.LIABILITIES]:
        accounts.extend(
            await account_repo.list_all(
                user_id=current_user.id,
                account_type=account_type,
                is_active=True
            )
        )

    balances = await balance_repo.get_latest_balances(user_id=current_user.id)
    balance_map = {
        (entry.account_id, entry.currency): entry.amount
        for entry in balances
    }

    response = []
    for account in accounts:
        balance = balance_map.get((account.id, account.currency))

        # Convert balance to display currency
        balance_in_display_currency = None
        if balance is not None:
            balance_in_display_currency = await rate_repo.convert_amount(
                amount=balance,
                from_currency=account.currency,
                to_currency=display_currency,
            )

        account_dict = {
            "id": account.id,
            "name": account.name,
            "account_type": account.account_type.value,
            "currency": account.currency,
            "description": account.description,
            "open_date": account.open_date,
            "close_date": account.close_date,
            "is_active": account.is_active,
            "balance": balance,
            "balance_in_display_currency": balance_in_display_currency,
            "display_currency": display_currency,
        }
        response.append(AccountResponse(**account_dict))

    return response


@router.post("/accounts", response_model=AccountResponse)
async def create_networth_account(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)

    first_component = account_data.name.split(":")[0]
    if first_component not in ["Assets", "Liabilities"]:
        raise HTTPException(
            status_code=400,
            detail="Account name must start with 'Assets:' or 'Liabilities:'"
        )

    try:
        account = await account_repo.create(
            user_id=current_user.id,
            name=account_data.name,
            open_date=account_data.open_date,
            currency=account_data.currency,
            description=account_data.description,
        )
        await session.commit()

        return AccountResponse(
            id=account.id,
            name=account.name,
            account_type=account.account_type.value,
            currency=account.currency,
            description=account.description,
            open_date=account.open_date,
            close_date=account.close_date,
            is_active=account.is_active,
            balance=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_networth_account(
    account_id: str,
    account_data: AccountCreate,
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)
    balance_repo = BalanceRepository(session)

    first_component = account_data.name.split(":")[0]
    if first_component not in ["Assets", "Liabilities"]:
        raise HTTPException(
            status_code=400,
            detail="Account name must start with 'Assets:' or 'Liabilities:'"
        )

    try:
        account = await account_repo.update(
            account_id=account_id,
            name=account_data.name,
            description=account_data.description,
        )

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        await session.commit()

        balances = await balance_repo.get_latest_balances()
        balance_map = {
            (entry.account_id, entry.currency): entry.amount
            for entry in balances
        }

        return AccountResponse(
            id=account.id,
            name=account.name,
            account_type=account.account_type.value,
            currency=account.currency,
            description=account.description,
            open_date=account.open_date,
            close_date=account.close_date,
            is_active=account.is_active,
            balance=balance_map.get((account.id, account.currency)),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/balances", response_model=BalanceResponse)
async def create_balance(
    balance_data: BalanceCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)
    balance_repo = BalanceRepository(session)

    account = await account_repo.get_by_id(balance_data.account_id, current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.account_type not in [AccountType.ASSETS, AccountType.LIABILITIES]:
        raise HTTPException(
            status_code=400,
            detail="Can only set balances for Assets or Liabilities accounts"
        )

    balance = await balance_repo.create_or_update(
        account_id=balance_data.account_id,
        date=balance_data.date,
        amount=balance_data.amount,
        currency=balance_data.currency,
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


@router.get("/summary", response_model=NetWorthResponse)
async def get_networth_summary(
    as_of_date: Optional[date_type] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if as_of_date is None:
        as_of_date = date_type.today()

    balance_repo = BalanceRepository(session)

    balances = await balance_repo.get_latest_balances(
        user_id=current_user.id,
        as_of_date=as_of_date
    )

    balance_responses = []
    for balance in balances:
        balance_responses.append(
            BalanceResponse(
                id=balance.id,
                account_id=balance.account.id,
                account_name=balance.account.name,
                account_type=balance.account.account_type.value,
                amount=balance.amount,
                currency=balance.currency,
                date=balance.date,
            )
        )

    summary_by_currency = {}
    for balance in balances:
        currency = balance.currency
        if currency not in summary_by_currency:
            summary_by_currency[currency] = {
                "total_assets": Decimal(0),
                "total_liabilities": Decimal(0),
            }

        if balance.account.account_type == AccountType.ASSETS:
            summary_by_currency[currency]["total_assets"] += balance.amount
        elif balance.account.account_type == AccountType.LIABILITIES:
            summary_by_currency[currency]["total_liabilities"] += balance.amount

    summaries = []
    for currency, totals in summary_by_currency.items():
        summaries.append(
            NetWorthSummary(
                currency=currency,
                total_assets=totals["total_assets"],
                total_liabilities=totals["total_liabilities"],
                net_worth=totals["total_assets"] - totals["total_liabilities"],
            )
        )

    summaries.sort(key=lambda x: x.currency)

    return NetWorthResponse(
        as_of_date=as_of_date,
        by_currency=summaries,
        entries=balance_responses,
    )


@router.patch("/accounts/{account_id}")
async def update_account(
    account_id: str,
    account_data: AccountCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)

    account = await account_repo.get_by_id(account_id, current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.name = account_data.name
    account.currency = account_data.currency
    if account_data.description is not None:
        account.description = account_data.description

    await session.commit()

    return AccountResponse(
        id=account.id,
        name=account.name,
        account_type=account.account_type.value,
        currency=account.currency,
        description=account.description,
        open_date=account.open_date,
        close_date=account.close_date,
        is_active=account.is_active,
        balance=None,
    )


@router.post("/accounts/{account_id}/close")
async def close_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    account_repo = AccountRepository(session)

    account = await account_repo.get_by_id(account_id, current_user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    closed_account = await account_repo.close_account(account_id, date_type.today())
    if not closed_account:
        raise HTTPException(status_code=404, detail="Account not found")

    await session.commit()
    return {"message": "Account closed successfully", "close_date": closed_account.close_date}


@router.delete("/balances/{balance_id}")
async def delete_balance(
    balance_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    balance_repo = BalanceRepository(session)

    deleted = await balance_repo.delete(balance_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Balance entry not found")

    await session.commit()
    return {"message": "Balance entry deleted successfully"}


@router.post("/exchange-rates", response_model=ExchangeRateResponse)
async def create_exchange_rate(
    rate_data: ExchangeRateCreate,
    session: AsyncSession = Depends(get_session),
):
    rate_repo = ExchangeRateRepository(session)

    rate = await rate_repo.create_or_update(
        date=rate_data.date,
        from_currency=rate_data.from_currency,
        to_currency=rate_data.to_currency,
        rate=rate_data.rate,
        source=rate_data.source,
    )
    await session.commit()

    return ExchangeRateResponse(
        id=rate.id,
        from_currency=rate.from_currency,
        to_currency=rate.to_currency,
        rate=rate.rate,
        date=rate.date,
        source=rate.source,
    )


@router.get("/exchange-rates", response_model=list[ExchangeRateResponse])
async def list_exchange_rates(
    from_currency: Optional[str] = None,
    to_currency: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    rate_repo = ExchangeRateRepository(session)

    rates = await rate_repo.list_all(
        from_currency=from_currency,
        to_currency=to_currency,
    )

    return [
        ExchangeRateResponse(
            id=rate.id,
            from_currency=rate.from_currency,
            to_currency=rate.to_currency,
            rate=rate.rate,
            date=rate.date,
            source=rate.source,
        )
        for rate in rates
    ]


@router.get("/exchange-rates/{from_currency}/{to_currency}")
async def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    as_of_date: Optional[date_type] = None,
    session: AsyncSession = Depends(get_session),
):
    rate_repo = ExchangeRateRepository(session)

    rate = await rate_repo.get_rate(
        from_currency=from_currency,
        to_currency=to_currency,
        as_of_date=as_of_date,
    )

    if rate is None:
        raise HTTPException(
            status_code=404,
            detail=f"No exchange rate found for {from_currency}/{to_currency}"
        )

    return {"from_currency": from_currency, "to_currency": to_currency, "rate": rate}


@router.delete("/exchange-rates/{rate_id}")
async def delete_exchange_rate(
    rate_id: str,
    session: AsyncSession = Depends(get_session),
):
    rate_repo = ExchangeRateRepository(session)

    deleted = await rate_repo.delete(rate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Exchange rate not found")

    await session.commit()
    return {"message": "Exchange rate deleted successfully"}


@router.get("/history")
async def get_networth_history(
    start_date: Optional[date_type] = None,
    end_date: Optional[date_type] = None,
    currency: str = "USD",
    session: AsyncSession = Depends(get_session),
):
    if end_date is None:
        end_date = date_type.today()
    if start_date is None:
        from datetime import timedelta
        start_date = end_date - timedelta(days=365)

    balance_repo = BalanceRepository(session)
    history = await balance_repo.get_networth_history(
        start_date=start_date,
        end_date=end_date,
        currency=currency,
    )

    return history


@router.get("/balances/history", response_model=list[BalanceResponse])
async def get_balance_history(
    start_date: Optional[date_type] = None,
    end_date: Optional[date_type] = None,
    account_id: Optional[str] = None,
    currency: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    if end_date is None:
        end_date = date_type.today()
    if start_date is None:
        from datetime import timedelta
        start_date = end_date - timedelta(days=365)

    balance_repo = BalanceRepository(session)
    balances = await balance_repo.get_history(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        currency=currency,
    )

    return [
        BalanceResponse(
            id=balance.id,
            account_id=balance.account.id,
            account_name=balance.account.name,
            account_type=balance.account.account_type.value,
            amount=balance.amount,
            currency=balance.currency,
            date=balance.date,
        )
        for balance in balances
    ]


@router.get("/allocation")
async def get_asset_allocation(
    as_of_date: Optional[date_type] = None,
    currency: str = "USD",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if as_of_date is None:
        as_of_date = date_type.today()

    balance_repo = BalanceRepository(session)
    balances = await balance_repo.get_latest_balances(
        user_id=current_user.id,
        as_of_date=as_of_date
    )

    allocation_by_category = {}
    total = Decimal(0)

    for balance in balances:
        # Filter by currency
        if balance.currency != currency:
            continue

        if balance.account.account_type != AccountType.ASSETS:
            continue

        name_parts = balance.account.name.split(":")
        category = name_parts[1] if len(name_parts) > 1 else "Other"

        if category not in allocation_by_category:
            allocation_by_category[category] = Decimal(0)

        allocation_by_category[category] += balance.amount
        total += balance.amount

    breakdown = []
    for category, amount in allocation_by_category.items():
        percentage = float((amount / total * 100) if total > 0 else 0)
        breakdown.append({
            "name": category,
            "value": float(amount),
            "percentage": round(percentage, 2),
            "currency": currency,
        })

    breakdown.sort(key=lambda x: x["value"], reverse=True)

    return {
        "total": float(total),
        "currency": currency,
        "breakdown": breakdown,
    }
