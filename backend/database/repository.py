"""
Repository pattern for database operations.

Provides clean abstractions for CRUD operations on accounting entities.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    Account,
    AccountType,
    Balance,
    ExchangeRate,
    IngestedDocument,
    IngestionRun,
    IngestionRunStatus,
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

    async def get_by_name(self, user_id: str, name: str) -> Account | None:
        """Get an account by its exact (user_id, name) — the find half of
        find-or-create, matching uq_account_user_name."""
        result = await self.session.execute(
            select(Account).where(Account.user_id == user_id, Account.name == name)
        )
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
    ) -> Account | None:
        """
        Update an account.

        Args:
            account_id: Account ID to update
            name: New account name (will update account_type automatically)
            description: New description

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
        source_document_id: str | None = None,
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
            if source_document_id is not None:
                balance.source_document_id = source_document_id
        else:
            balance = Balance(
                account_id=account_id,
                date=date,
                amount=amount,
                currency=currency,
                is_verified=True,
                source_document_id=source_document_id,
            )
            self.session.add(balance)

        await self.session.flush()
        return balance

    async def get_latest_balances(
        self,
        user_id: str | None = None,
        as_of_date: date | None = None,
        include_inactive: bool = False,
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
            .join(Account, Balance.account_id == Account.id)
            .options(selectinload(Balance.account), selectinload(Balance.source_document))
        )

        if user_id is not None:
            query = query.where(Account.user_id == user_id)
        if not include_inactive:
            query = query.where(Account.is_active == True)

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
        include_inactive: bool = False,
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
        if not include_inactive:
            query = query.where(Account.is_active == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())


class IngestionRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: str, file_count: int) -> IngestionRun:
        run = IngestionRun(user_id=user_id, file_count=file_count)
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_by_id(self, run_id: str, user_id: str) -> IngestionRun | None:
        result = await self.session.execute(
            select(IngestionRun).where(
                IngestionRun.id == run_id, IngestionRun.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def mark_processing(self, run_id: str) -> IngestionRun | None:
        result = await self.session.execute(
            select(IngestionRun).where(IngestionRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = IngestionRunStatus.PROCESSING
            await self.session.flush()
        return run

    async def mark_succeeded(
        self,
        run_id: str,
        positions_count: int,
        warnings: list[str],
        llm_call_count: int | None = None,
        llm_input_tokens: int | None = None,
        llm_output_tokens: int | None = None,
        llm_cache_creation_tokens: int | None = None,
        llm_cache_read_tokens: int | None = None,
        llm_estimated_cost_usd: Decimal | None = None,
    ) -> IngestionRun | None:
        result = await self.session.execute(
            select(IngestionRun).where(IngestionRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = IngestionRunStatus.SUCCEEDED
            run.positions_count = positions_count
            run.warnings = warnings
            run.completed_at = datetime.now()
            run.llm_call_count = llm_call_count
            run.llm_input_tokens = llm_input_tokens
            run.llm_output_tokens = llm_output_tokens
            run.llm_cache_creation_tokens = llm_cache_creation_tokens
            run.llm_cache_read_tokens = llm_cache_read_tokens
            run.llm_estimated_cost_usd = llm_estimated_cost_usd
            await self.session.flush()
        return run

    async def mark_failed(self, run_id: str, error_message: str) -> IngestionRun | None:
        result = await self.session.execute(
            select(IngestionRun).where(IngestionRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = IngestionRunStatus.FAILED
            run.error_message = error_message
            run.completed_at = datetime.now()
            await self.session.flush()
        return run


class IngestedDocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(
        self,
        ingestion_run_id: str,
        source: str | None,
        doc_issued_at: datetime,
    ) -> IngestedDocument:
        existing = await self.session.execute(
            select(IngestedDocument).where(
                and_(
                    IngestedDocument.ingestion_run_id == ingestion_run_id,
                    IngestedDocument.source == source,
                    IngestedDocument.doc_issued_at == doc_issued_at,
                )
            )
        )
        document = existing.scalar_one_or_none()
        if document is None:
            document = IngestedDocument(
                ingestion_run_id=ingestion_run_id,
                source=source,
                doc_issued_at=doc_issued_at,
            )
            self.session.add(document)
            await self.session.flush()
        return document


@dataclass
class ConversionResult:
    amount: Decimal
    rate_available: bool


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

    async def _get_rate_or_inverse(
        self,
        from_currency: str,
        to_currency: str,
        as_of_date: date,
    ) -> Decimal | None:
        rate = await self.get_rate(from_currency, to_currency, as_of_date)
        if rate:
            return rate

        inverse_rate = await self.get_rate(to_currency, from_currency, as_of_date)
        if inverse_rate and inverse_rate != 0:
            return Decimal(1) / inverse_rate

        return None

    async def convert_amount(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        as_of_date: date | None = None,
    ) -> ConversionResult:
        """
        Convert an amount from one currency to another using exchange rates.
        Tries a direct rate, then an inverse rate, then triangulates through
        USD as a bridge currency (all seed data is USD-anchored). If no path
        exists, returns the raw amount with rate_available=False rather than
        silently pretending a conversion happened.
        """
        if from_currency == to_currency:
            return ConversionResult(amount=amount, rate_available=True)

        if as_of_date is None:
            as_of_date = date.today()

        direct = await self._get_rate_or_inverse(from_currency, to_currency, as_of_date)
        if direct is not None:
            return ConversionResult(amount=amount * direct, rate_available=True)

        if from_currency != "USD" and to_currency != "USD":
            to_usd = await self._get_rate_or_inverse(from_currency, "USD", as_of_date)
            from_usd = await self._get_rate_or_inverse("USD", to_currency, as_of_date)
            if to_usd is not None and from_usd is not None:
                return ConversionResult(amount=amount * to_usd * from_usd, rate_available=True)

        return ConversionResult(amount=amount, rate_available=False)
