from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from auth_utils import create_access_token
from database.models import User
from database.repository import AccountRepository, BalanceRepository, ExchangeRateRepository
from database.session import get_session


@pytest_asyncio.fixture
async def balance_repo(session: AsyncSession) -> BalanceRepository:
    return BalanceRepository(session)


@pytest_asyncio.fixture
async def exchange_rate_repo(session: AsyncSession) -> ExchangeRateRepository:
    return ExchangeRateRepository(session)


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        email="currency-test@example.com",
        username="currency_test_user",
        hashed_password="unused-in-these-tests",
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = create_access_token(
        data={"sub": test_user.id, "username": test_user.username, "email": test_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestAccountsDisplayCurrency:
    async def test_converts_balance_to_display_currency(
        self,
        client: AsyncClient,
        auth_headers: dict,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        exchange_rate_repo: ExchangeRateRepository,
        test_user: User,
    ):
        await exchange_rate_repo.create_or_update(
            date=date(2024, 1, 1),
            from_currency="USD",
            to_currency="INR",
            rate=Decimal("83.0"),
        )
        account = await account_repo.create(
            name="Assets:Bank:USDChecking",
            open_date=date(2024, 1, 1),
            currency="USD",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2024, 1, 1), amount=Decimal("100.00"), currency="USD"
        )

        response = await client.get(
            "/api/accounts?display_currency=INR", headers=auth_headers
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["balance"] == "100.0000"
        assert body[0]["rate_available"] is True
        assert Decimal(body[0]["balance_in_display_currency"]) == Decimal("8300.0")

    async def test_flags_rate_unavailable_instead_of_silently_echoing(
        self,
        client: AsyncClient,
        auth_headers: dict,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        test_user: User,
    ):
        # No exchange rates seeded at all for this pair.
        account = await account_repo.create(
            name="Assets:Bank:JPYSavings",
            open_date=date(2024, 1, 1),
            currency="JPY",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2024, 1, 1), amount=Decimal("10000"), currency="JPY"
        )

        response = await client.get(
            "/api/accounts?display_currency=EUR", headers=auth_headers
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["rate_available"] is False
        assert body[0]["balance_in_display_currency"] is None


@pytest.mark.asyncio
class TestAllocationDisplayCurrency:
    async def test_converts_instead_of_dropping_mismatched_currency(
        self,
        client: AsyncClient,
        auth_headers: dict,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        exchange_rate_repo: ExchangeRateRepository,
        test_user: User,
    ):
        await exchange_rate_repo.create_or_update(
            date=date(2024, 1, 1),
            from_currency="USD",
            to_currency="INR",
            rate=Decimal("83.0"),
        )
        account = await account_repo.create(
            name="Assets:Bank:USDChecking",
            open_date=date(2024, 1, 1),
            currency="USD",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2024, 1, 1), amount=Decimal("100.00"), currency="USD"
        )

        response = await client.get("/api/allocation?currency=INR", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        # Previously this account would have been silently dropped because its
        # native currency (USD) didn't match the requested one (INR).
        assert body["total"] == pytest.approx(8300.0)
        assert len(body["breakdown"]) == 1
        assert body["excluded_count"] == 0

    async def test_excludes_and_counts_rate_unavailable_accounts(
        self,
        client: AsyncClient,
        auth_headers: dict,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        test_user: User,
    ):
        account = await account_repo.create(
            name="Assets:Bank:JPYSavings",
            open_date=date(2024, 1, 1),
            currency="JPY",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2024, 1, 1), amount=Decimal("10000"), currency="JPY"
        )

        response = await client.get("/api/allocation?currency=EUR", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["breakdown"] == []
        assert body["excluded_count"] == 1
