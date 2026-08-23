import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ExchangeRate
from database.repository import ExchangeRateRepository
from database.session import session_context
from jobs.config import get_exchange_rate_sync_settings

logger = logging.getLogger(__name__)

SOURCE_NAME = "open.er-api.com"


async def fetch_rate(base_currency: str, quote_currency: str) -> Decimal:
    settings = get_exchange_rate_sync_settings()
    url = settings.exchange_rate_api_url.format(base=base_currency)

    async with httpx.AsyncClient(timeout=10.0) as http_client:
        response = await http_client.get(url)
        response.raise_for_status()
        payload = response.json()

    if payload.get("result") != "success":
        raise ValueError(f"exchange rate API returned non-success result: {payload.get('result')!r}")

    rates = payload.get("rates", {})
    if quote_currency not in rates:
        raise ValueError(f"{quote_currency} missing from exchange rate API response")

    try:
        return Decimal(str(rates[quote_currency]))
    except InvalidOperation as exc:
        raise ValueError(f"invalid rate value for {quote_currency}: {rates[quote_currency]!r}") from exc


async def store_rate(
    session: AsyncSession,
    base_currency: str,
    quote_currency: str,
    rate: Decimal,
) -> ExchangeRate:
    return await ExchangeRateRepository(session).create_or_update(
        date=date.today(),
        from_currency=base_currency,
        to_currency=quote_currency,
        rate=rate,
        source=SOURCE_NAME,
    )


async def sync_exchange_rates() -> None:
    settings = get_exchange_rate_sync_settings()
    base = settings.exchange_rate_base_currency
    quote = settings.exchange_rate_quote_currency

    try:
        rate = await fetch_rate(base, quote)
    except Exception:
        logger.exception("Nightly exchange rate sync failed to fetch %s/%s", base, quote)
        return

    try:
        async with session_context() as session:
            await store_rate(session, base, quote, rate)
    except Exception:
        logger.exception("Nightly exchange rate sync failed to store %s/%s", base, quote)
        return

    logger.info("Synced exchange rate %s/%s = %s", base, quote, rate)
