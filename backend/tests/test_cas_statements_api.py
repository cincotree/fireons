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
from tests.fixtures.generate_cas_fixture import FIXTURES_DIR, TEST_CAS_PDF_PASSWORD


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


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
async def test_user(session: AsyncSession) -> User:
    user = User(
        email="cas-statements-test@example.com",
        username="cas_statements_test_user",
        hashed_password="unused-in-these-tests",
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = create_access_token(
        data={"sub": test_user.id, "username": test_user.username, "email": test_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


async def _parse(client: AsyncClient, auth_headers: dict, fixture_name: str) -> dict:
    response = await client.post(
        "/api/statements/cas/parse",
        headers=auth_headers,
        files={"file": (fixture_name, _fixture_bytes(fixture_name), "application/pdf")},
        data={"password": TEST_CAS_PDF_PASSWORD, "source": "CAMS"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _to_confirm_holding(preview: dict) -> dict:
    return {
        "amc": preview["amc"],
        "scheme_name": preview["scheme_name"],
        "folio_number": preview["folio_number"],
        "isin": preview["isin"],
        "units": preview["units"],
        "nav": preview["nav"],
        "market_value": preview["market_value"],
        "valuation_date": preview["valuation_date"],
        "account_name": preview["suggested_account_name"],
        "currency": "INR",
        "source": preview["source"],
    }


@pytest.mark.asyncio
class TestParseCASEndpoint:
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/statements/cas/parse",
            files={"file": ("cas.pdf", _fixture_bytes("cas_valid.pdf"), "application/pdf")},
            data={"password": TEST_CAS_PDF_PASSWORD},
        )
        assert response.status_code == 403

    async def test_happy_path_all_new_and_no_writes(
        self, client: AsyncClient, auth_headers: dict, session: AsyncSession
    ):
        body = await _parse(client, auth_headers, "cas_valid.pdf")

        assert body["statement_date"] == "2025-03-31"
        assert len(body["holdings"]) == 4
        assert all(h["existing_account_id"] is None for h in body["holdings"])
        assert all(h["source"] == "CAMS" for h in body["holdings"])

        account_repo = AccountRepository(session)
        assert await account_repo.list_all() == []

    async def test_wrong_password_returns_422(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/statements/cas/parse",
            headers=auth_headers,
            files={"file": ("cas.pdf", _fixture_bytes("cas_valid.pdf"), "application/pdf")},
            data={"password": "wrong-password"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestConfirmCASEndpoint:
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/statements/cas/confirm", json={"holdings": []})
        assert response.status_code == 403

    async def test_rejects_empty_holdings(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/statements/cas/confirm", headers=auth_headers, json={"holdings": []}
        )
        assert response.status_code == 400

    async def test_happy_path_creates_accounts_and_balances(
        self, client: AsyncClient, auth_headers: dict, test_user: User, session: AsyncSession
    ):
        parsed = await _parse(client, auth_headers, "cas_valid.pdf")
        holdings = [_to_confirm_holding(h) for h in parsed["holdings"]]

        response = await client.post(
            "/api/statements/cas/confirm",
            headers=auth_headers,
            json={"holdings": holdings},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["created_count"] == 4
        assert body["updated_count"] == 0
        assert all(r["was_created"] for r in body["results"])

        account_repo = AccountRepository(session)
        accounts = await account_repo.list_all(user_id=test_user.id)
        assert len(accounts) == 4
        alpha = await account_repo.get_by_name(
            "Assets:Investment:MutualFund:Aditya Birla Sun Life:1234567:"
            "T001 - Test Bluechip Fund - Growth-Direct Plan (Non-Demat)",
            test_user.id,
        )
        assert alpha is not None
        assert alpha.meta["amc"] == "Aditya Birla Sun Life"
        assert alpha.meta["folio_number"] == "1234567"

    async def test_partial_selection_only_creates_selected_subset(
        self, client: AsyncClient, auth_headers: dict, test_user: User, session: AsyncSession
    ):
        parsed = await _parse(client, auth_headers, "cas_valid.pdf")
        holdings = [_to_confirm_holding(parsed["holdings"][0])]

        response = await client.post(
            "/api/statements/cas/confirm",
            headers=auth_headers,
            json={"holdings": holdings},
        )
        assert response.status_code == 200
        assert response.json()["created_count"] == 1

        account_repo = AccountRepository(session)
        accounts = await account_repo.list_all(user_id=test_user.id)
        assert len(accounts) == 1

    async def test_bad_account_name_prefix_aborts_whole_request(
        self, client: AsyncClient, auth_headers: dict, test_user: User, session: AsyncSession
    ):
        parsed = await _parse(client, auth_headers, "cas_valid.pdf")
        holdings = [_to_confirm_holding(h) for h in parsed["holdings"]]
        holdings[-1]["account_name"] = "NotAValidPrefix:Whatever"

        response = await client.post(
            "/api/statements/cas/confirm",
            headers=auth_headers,
            json={"holdings": holdings},
        )
        assert response.status_code == 400

        account_repo = AccountRepository(session)
        assert await account_repo.list_all(user_id=test_user.id) == []

    async def test_reupload_updates_existing_account_instead_of_duplicating(
        self, client: AsyncClient, auth_headers: dict, test_user: User, session: AsyncSession
    ):
        before = await _parse(client, auth_headers, "cas_reupload_before.pdf")
        before_holding = _to_confirm_holding(before["holdings"][0])

        confirm_response = await client.post(
            "/api/statements/cas/confirm",
            headers=auth_headers,
            json={"holdings": [before_holding]},
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["created_count"] == 1
        assert confirm_response.json()["updated_count"] == 0

        after = await _parse(client, auth_headers, "cas_reupload_after.pdf")
        assert after["holdings"][0]["existing_account_id"] is not None
        after_holding = _to_confirm_holding(after["holdings"][0])

        confirm_response = await client.post(
            "/api/statements/cas/confirm",
            headers=auth_headers,
            json={"holdings": [after_holding]},
        )
        assert confirm_response.status_code == 200
        body = confirm_response.json()
        assert body["created_count"] == 0
        assert body["updated_count"] == 1

        account_repo = AccountRepository(session)
        accounts = await account_repo.list_all(user_id=test_user.id)
        assert len(accounts) == 1

        balance_repo = BalanceRepository(session)
        balances = await balance_repo.get_history(
            start_date=date(2000, 1, 1),
            end_date=date(2100, 1, 1),
            account_id=accounts[0].id,
        )
        # Two snapshots on one account (one per statement date) — a
        # re-upload must not create a second account for the same holding.
        assert len(balances) == 2
        latest = max(balances, key=lambda b: b.date)
        assert latest.amount == Decimal("60500.00")
        assert latest.date.isoformat() == "2025-04-30"
