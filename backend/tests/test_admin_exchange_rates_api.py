from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import app
from auth_utils import create_access_token, create_admin_token, get_password_hash
from database.repository import AdminRepository, ExchangeRateRepository
from database.session import get_session


@pytest_asyncio.fixture
async def client(session):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def headers(session) -> dict:
    admin = await AdminRepository(session).create("rates_admin", get_password_hash("correct-horse-battery"))
    token = create_admin_token(admin.id, admin.username)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def rates(session):
    repository = ExchangeRateRepository(session)
    await repository.create(date(2026, 11, 10), "USD", "INR", Decimal("83.5"), "open.er-api.com")
    await repository.create(date(2026, 11, 11), "USD", "INR", Decimal("83.7"), "open.er-api.com")
    await repository.create(date(2026, 11, 11), "EUR", "USD", Decimal("1.08"))


@pytest.mark.asyncio
async def test_requires_an_admin_token(client, rates):
    assert (await client.get("/admin/exchange-rates")).status_code in (401, 403)
    response = await client.get("/admin/exchange-rates", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rejects_regular_user_tokens(client, rates):
    token = create_access_token({"sub": "u1", "username": "u", "email": "u@example.com"})

    response = await client.get("/admin/exchange-rates", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_lists_rates_newest_first(client, headers, rates):
    response = await client.get("/admin/exchange-rates", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [(row["date"], row["from_currency"], row["to_currency"]) for row in body] == [
        ("2026-11-11", "EUR", "USD"),
        ("2026-11-11", "USD", "INR"),
        ("2026-11-10", "USD", "INR"),
    ]
    assert Decimal(body[1]["rate"]) == Decimal("83.7")
    assert body[1]["source"] == "open.er-api.com"


@pytest.mark.asyncio
async def test_filters_by_currency_case_insensitively(client, headers, rates):
    response = await client.get("/admin/exchange-rates?from_currency=usd&to_currency=inr", headers=headers)

    assert [row["date"] for row in response.json()] == ["2026-11-11", "2026-11-10"]


@pytest.mark.asyncio
async def test_limits_rows(client, headers, rates):
    response = await client.get("/admin/exchange-rates?limit=1", headers=headers)

    assert len(response.json()) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["limit=0", "limit=501", "from_currency="])
async def test_validates_query(client, headers, query):
    assert (await client.get(f"/admin/exchange-rates?{query}", headers=headers)).status_code == 422
