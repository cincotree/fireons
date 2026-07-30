from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from auth_utils import create_access_token
from database.models import User
from database.repository import AccountRepository, BalanceRepository
from database.session import get_session


@pytest_asyncio.fixture
async def balance_repo(session: AsyncSession) -> BalanceRepository:
    return BalanceRepository(session)


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        email="closure-test@example.com",
        username="closure_test_user",
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
class TestGetLatestBalancesExcludesClosedAccounts:
    async def test_excludes_closed_account_by_default(
        self,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        test_user: User,
    ):
        account = await account_repo.create(
            name="Assets:Bank:ToClose",
            open_date=date(2026, 1, 1),
            currency="USD",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2026, 1, 1), amount=Decimal("500.00"), currency="USD"
        )
        await account_repo.close_account(account.id, date(2026, 1, 2))

        balances = await balance_repo.get_latest_balances(user_id=test_user.id)

        assert balances == []

    async def test_includes_active_account(
        self,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        test_user: User,
    ):
        account = await account_repo.create(
            name="Assets:Bank:StillOpen",
            open_date=date(2026, 1, 1),
            currency="USD",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2026, 1, 1), amount=Decimal("500.00"), currency="USD"
        )

        balances = await balance_repo.get_latest_balances(user_id=test_user.id)

        assert len(balances) == 1
        assert balances[0].account_id == account.id

    async def test_include_inactive_true_returns_closed_account(
        self,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        test_user: User,
    ):
        account = await account_repo.create(
            name="Assets:Bank:ToClose",
            open_date=date(2026, 1, 1),
            currency="USD",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2026, 1, 1), amount=Decimal("500.00"), currency="USD"
        )
        await account_repo.close_account(account.id, date(2026, 1, 2))

        balances = await balance_repo.get_latest_balances(
            user_id=test_user.id, include_inactive=True
        )

        assert len(balances) == 1
        assert balances[0].account_id == account.id


@pytest.mark.asyncio
class TestGetHistoryExcludesClosedAccounts:
    async def test_excludes_closed_account_by_default(
        self,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        test_user: User,
    ):
        account = await account_repo.create(
            name="Assets:Bank:ToClose",
            open_date=date(2026, 1, 1),
            currency="USD",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2026, 1, 1), amount=Decimal("500.00"), currency="USD"
        )
        await account_repo.close_account(account.id, date(2026, 1, 2))

        history = await balance_repo.get_history(
            start_date=date(2025, 1, 1), end_date=date(2026, 12, 31), user_id=test_user.id
        )

        assert history == []

    async def test_include_inactive_true_returns_closed_account(
        self,
        account_repo: AccountRepository,
        balance_repo: BalanceRepository,
        test_user: User,
    ):
        account = await account_repo.create(
            name="Assets:Bank:ToClose",
            open_date=date(2026, 1, 1),
            currency="USD",
            user_id=test_user.id,
        )
        await balance_repo.create_or_update(
            account_id=account.id, date=date(2026, 1, 1), amount=Decimal("500.00"), currency="USD"
        )
        await account_repo.close_account(account.id, date(2026, 1, 2))

        history = await balance_repo.get_history(
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
            user_id=test_user.id,
            include_inactive=True,
        )

        assert len(history) == 1
        assert history[0].account_id == account.id


@pytest.mark.asyncio
class TestClosedAccountExcludedFromDashboardEndpoints:
    async def _create_and_close_account_with_balance(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        create_response = await client.post(
            "/api/accounts",
            headers=auth_headers,
            json={"name": "Assets:Bank:ClosureBugTest", "currency": "USD"},
        )
        assert create_response.status_code == 200
        account_id = create_response.json()["id"]

        balance_response = await client.post(
            f"/api/accounts/{account_id}/balance",
            headers=auth_headers,
            json={"amount": "500.00", "currency": "USD"},
        )
        assert balance_response.status_code == 200

        close_response = await client.post(
            f"/api/accounts/{account_id}/close", headers=auth_headers
        )
        assert close_response.status_code == 200

    async def test_accounts_endpoint_excludes_closed_account(
        self, client: AsyncClient, auth_headers: dict
    ):
        await self._create_and_close_account_with_balance(client, auth_headers)

        response = await client.get("/api/accounts?display_currency=USD", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    async def test_allocation_excludes_closed_account(
        self, client: AsyncClient, auth_headers: dict
    ):
        await self._create_and_close_account_with_balance(client, auth_headers)

        response = await client.get("/api/allocation?currency=USD", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["breakdown"] == []

    async def test_networth_history_excludes_closed_account(
        self, client: AsyncClient, auth_headers: dict
    ):
        await self._create_and_close_account_with_balance(client, auth_headers)

        response = await client.get("/api/networth-history?currency=USD", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []
