"""
Repository pattern for database operations.

Provides clean abstractions for CRUD operations on accounting entities.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    Account,
    AccountType,
    Balance,
    ExchangeRate,
)


class AccountRepository:
    """Repository for Account operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        open_date: date,
        currency: str = "USD",
        description: str | None = None,
        meta: dict | None = None,
        user_id: str | None = None,
    ) -> Account:
        """
        Create a new account.

        Args:
            name: Full account name (e.g., "Assets:Bank:Checking")
            open_date: Date the account was opened
            currency: Default currency for the account
            description: Optional description
            meta: Optional metadata dictionary

        Returns:
            The created Account instance
        """
        first_component = name.split(":")[0]
        try:
            account_type = AccountType(first_component)
        except ValueError:
            raise ValueError(
                f"Invalid account type '{first_component}'. "
                f"Must be one of: {[t.value for t in AccountType]}"
            )

        account = Account(
            name=name,
            account_type=account_type,
            currency=currency,
            open_date=open_date,
            description=description,
            meta=meta,
            user_id=user_id,
        )
        self.session.add(account)
        await self.session.flush()
        return account

    async def get_by_id(self, account_id: str, user_id: str | None = None) -> Account | None:
        """Get an account by ID."""
        query = select(Account).where(Account.id == account_id)
        if user_id is not None:
            query = query.where(Account.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, user_id: str | None = None) -> Account | None:
        """Get an account by its full name."""
        query = select(Account).where(Account.name == name)
        if user_id is not None:
            query = query.where(Account.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        user_id: str | None = None,
        account_type: AccountType | None = None,
        is_active: bool | None = None,
    ) -> list[Account]:
        """
        List all accounts with optional filters.

        Args:
            user_id: Filter by user ID
            account_type: Filter by account type
            is_active: Filter by active status

        Returns:
            List of Account instances
        """
        query = select(Account).order_by(Account.name)

        if user_id is not None:
            query = query.where(Account.user_id == user_id)
        if account_type is not None:
            query = query.where(Account.account_type == account_type)
        if is_active is not None:
            query = query.where(Account.is_active == is_active)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def close_account(self, account_id: str, close_date: date) -> Account | None:
        """
        Close an account.

        Args:
            account_id: Account ID to close
            close_date: Date to close the account

        Returns:
            Updated Account or None if not found
        """
        account = await self.get_by_id(account_id)
        if account:
            account.close_date = close_date
            account.is_active = False
            await self.session.flush()
        return account

    async def update(
        self,
        account_id: str,
        name: str | None = None,
        description: str | None = None,
        meta: dict | None = None,
    ) -> Account | None:
        """
        Update an account.

        Args:
            account_id: Account ID to update
            name: New account name (will update account_type automatically)
            description: New description
            meta: New metadata dictionary (replaces any existing meta)

        Returns:
            Updated Account or None if not found
        """
        account = await self.get_by_id(account_id)
        if not account:
            return None

        if name is not None:
            first_component = name.split(":")[0]
            try:
                account_type = AccountType(first_component)
            except ValueError:
                raise ValueError(
                    f"Invalid account type '{first_component}'. "
                    f"Must be one of: {[t.value for t in AccountType]}"
                )
            account.name = name
            account.account_type = account_type

        if description is not None:
            account.description = description

        if meta is not None:
            account.meta = meta

        await self.session.flush()
        return account


class TransactionRepository:
    """Repository for Transaction operations.

    Minimal stub: transaction/posting import is out of scope for now
    (see BACKLOG milestone G). Exists so `database.repository` exposes
    the name tests/conftest.py already imports.
    """

    def __init__(self, session: AsyncSession):
        self.session = session


class BalanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update(
        self,
        account_id: str,
        date: date,
        amount: Decimal,
        currency: str,
    ) -> Balance:
        existing = await self.session.execute(
            select(Balance).where(
                and_(
                    Balance.account_id == account_id,
                    Balance.date == date,
                    Balance.currency == currency,
                )
            )
        )
        balance = existing.scalar_one_or_none()

        if balance:
            balance.amount = amount
        else:
            balance = Balance(
                account_id=account_id,
                date=date,
                amount=amount,
                currency=currency,
                is_verified=True,
            )
            self.session.add(balance)

        await self.session.flush()
        return balance

    async def get_latest_balances(
        self, user_id: str | None = None, as_of_date: date | None = None
    ) -> list[Balance]:
        if as_of_date is None:
            as_of_date = date.today()

        subquery = (
            select(
                Balance.account_id,
                Balance.currency,
                func.max(Balance.date).label("max_date"),
            )
            .where(Balance.date <= as_of_date)
            .group_by(Balance.account_id, Balance.currency)
            .subquery()
        )

        query = (
            select(Balance)
            .join(
                subquery,
                and_(
                    Balance.account_id == subquery.c.account_id,
                    Balance.currency == subquery.c.currency,
                    Balance.date == subquery.c.max_date,
                ),
            )
            .options(selectinload(Balance.account))
        )

        if user_id is not None:
            query = query.join(Account, Balance.account_id == Account.id).where(
                Account.user_id == user_id
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, balance_id: str, user_id: str) -> bool:
        result = await self.session.execute(
            select(Balance)
            .join(Account, Balance.account_id == Account.id)
            .where(
                and_(
                    Balance.id == balance_id,
                    Account.user_id == user_id
                )
            )
        )
        balance = result.scalar_one_or_none()
        if balance:
            await self.session.delete(balance)
            await self.session.flush()
            return True
        return False

    async def get_history(
        self,
        start_date: date,
        end_date: date,
        user_id: str | None = None,
        account_id: str | None = None,
        currency: str | None = None,
    ) -> list[Balance]:
        query = (
            select(Balance)
            .join(Account, Balance.account_id == Account.id)
            .where(
                and_(
                    Balance.date >= start_date,
                    Balance.date <= end_date,
                )
            )
            .options(selectinload(Balance.account))
            .order_by(Balance.date)
        )

        if user_id:
            query = query.where(Account.user_id == user_id)
        if account_id:
            query = query.where(Balance.account_id == account_id)
        if currency:
            query = query.where(Balance.currency == currency)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class ExchangeRateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update(
        self,
        date: date,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        source: str | None = None,
    ) -> ExchangeRate:
        existing = await self.session.execute(
            select(ExchangeRate).where(
                and_(
                    ExchangeRate.date == date,
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                )
            )
        )
        exchange_rate = existing.scalar_one_or_none()

        if exchange_rate:
            exchange_rate.rate = rate
            if source:
                exchange_rate.source = source
        else:
            exchange_rate = ExchangeRate(
                date=date,
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                source=source,
            )
            self.session.add(exchange_rate)

        await self.session.flush()
        return exchange_rate

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        as_of_date: date | None = None,
    ) -> Decimal | None:
        if as_of_date is None:
            as_of_date = date.today()

        result = await self.session.execute(
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.date <= as_of_date,
                )
            )
            .order_by(ExchangeRate.date.desc())
            .limit(1)
        )
        rate_obj = result.scalar_one_or_none()
        return rate_obj.rate if rate_obj else None

    async def list_all(
        self,
        from_currency: str | None = None,
        to_currency: str | None = None,
    ) -> list[ExchangeRate]:
        query = select(ExchangeRate).order_by(
            ExchangeRate.date.desc(),
            ExchangeRate.from_currency,
            ExchangeRate.to_currency,
        )

        if from_currency:
            query = query.where(ExchangeRate.from_currency == from_currency)
        if to_currency:
            query = query.where(ExchangeRate.to_currency == to_currency)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, exchange_rate_id: str) -> bool:
        result = await self.session.execute(
            select(ExchangeRate).where(ExchangeRate.id == exchange_rate_id)
        )
        rate = result.scalar_one_or_none()
        if rate:
            await self.session.delete(rate)
            await self.session.flush()
            return True
        return False

    async def convert_amount(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        as_of_date: date | None = None,
    ) -> Decimal:
        """
        Convert an amount from one currency to another using exchange rates.
        Returns the amount unchanged if currencies are the same.
        """
        if from_currency == to_currency:
            return amount

        if as_of_date is None:
            as_of_date = date.today()


        rate = await self.get_rate(from_currency, to_currency, as_of_date)
        if rate:
            return amount * rate


        inverse_rate = await self.get_rate(to_currency, from_currency, as_of_date)
        if inverse_rate and inverse_rate != 0:
            return amount / inverse_rate

        return amount
