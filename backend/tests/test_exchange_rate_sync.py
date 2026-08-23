from datetime import date
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from database.repository import ExchangeRateRepository
from jobs.exchange_rate_sync import fetch_rate, store_rate


@pytest_asyncio.fixture
async def exchange_rate_repo(session: AsyncSession) -> ExchangeRateRepository:
    return ExchangeRateRepository(session)


_RealAsyncClient = httpx.AsyncClient


def _patch_transport(monkeypatch, payload: dict, status_code: int = 200) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    transport = httpx.MockTransport(handler)

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = transport
        return _RealAsyncClient(*args, **kwargs)

    monkeypatch.setattr("jobs.exchange_rate_sync.httpx.AsyncClient", fake_async_client)


@pytest.mark.asyncio
async def test_fetch_rate_parses_successful_response(monkeypatch):
    _patch_transport(monkeypatch, {"result": "success", "rates": {"INR": "83.123456"}})

    rate = await fetch_rate("USD", "INR")

    assert rate == Decimal("83.123456")


@pytest.mark.asyncio
async def test_fetch_rate_raises_on_non_success_result(monkeypatch):
    _patch_transport(monkeypatch, {"result": "error", "rates": {}})

    with pytest.raises(ValueError, match="non-success result"):
        await fetch_rate("USD", "INR")


@pytest.mark.asyncio
async def test_fetch_rate_raises_when_quote_currency_missing(monkeypatch):
    _patch_transport(monkeypatch, {"result": "success", "rates": {"EUR": "0.9"}})

    with pytest.raises(ValueError, match="INR missing"):
        await fetch_rate("USD", "INR")


@pytest.mark.asyncio
async def test_fetch_rate_raises_on_http_error(monkeypatch):
    _patch_transport(monkeypatch, {}, status_code=500)

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_rate("USD", "INR")


@pytest.mark.asyncio
async def test_store_rate_creates_new_row(
    session: AsyncSession,
    exchange_rate_repo: ExchangeRateRepository,
):
    stored = await store_rate(session, "USD", "INR", Decimal("83.5"))
    await session.commit()

    assert stored.from_currency == "USD"
    assert stored.to_currency == "INR"
    assert stored.rate == Decimal("83.5")
    assert stored.source == "open.er-api.com"
    assert stored.date == date.today()

    fetched = await exchange_rate_repo.get_rate("USD", "INR")
    assert fetched == Decimal("83.5")


@pytest.mark.asyncio
async def test_store_rate_overwrites_existing_row_for_same_day(
    session: AsyncSession,
    exchange_rate_repo: ExchangeRateRepository,
):
    await store_rate(session, "USD", "INR", Decimal("83.0"))
    await session.commit()

    await store_rate(session, "USD", "INR", Decimal("83.9"))
    await session.commit()

    fetched = await exchange_rate_repo.get_rate("USD", "INR")
    assert fetched == Decimal("83.9")
