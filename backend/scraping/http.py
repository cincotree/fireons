import asyncio
import time
from typing import Awaitable, Callable

import httpx

from scraping.config import ScrapeSettings, get_scrape_settings
from scraping.types import ScrapeHttpError

RETRYABLE_STATUSES = {429, 500, 502, 503, 504, 530}
MAX_BACKOFF_SECONDS = 60.0
MAX_RETRY_AFTER_SECONDS = 120.0


class PoliteClient:
    def __init__(
        self,
        settings: ScrapeSettings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings or get_scrape_settings()
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None
        self._client = httpx.AsyncClient(
            transport=transport,
            timeout=self.settings.scrape_timeout_seconds,
            headers={"User-Agent": self.settings.scrape_user_agent},
            follow_redirects=True,
        )
        self.request_count = 0

    async def __aenter__(self) -> "PoliteClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._client.aclose()

    async def _wait_for_turn(self) -> None:
        if self._last_request_at is not None:
            elapsed = self._clock() - self._last_request_at
            remaining = self.settings.scrape_min_interval_seconds - elapsed
            if remaining > 0:
                await self._sleep(remaining)
        self._last_request_at = self._clock()

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        header = response.headers.get("Retry-After")
        if header is None:
            return None
        try:
            return min(max(float(header), 0.0), MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            return None

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        attempts = self.settings.scrape_max_retries + 1
        last_problem = "no attempt made"
        for attempt in range(attempts):
            await self._wait_for_turn()
            self.request_count += 1
            retry_after = None
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                last_problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code < 400:
                    return response
                if response.status_code not in RETRYABLE_STATUSES:
                    raise ScrapeHttpError(f"{method} {url} returned {response.status_code}")
                last_problem = f"HTTP {response.status_code}"
                retry_after = self._retry_after(response)
            if attempt < attempts - 1:
                backoff = min(2.0 * (2**attempt), MAX_BACKOFF_SECONDS)
                await self._sleep(retry_after if retry_after is not None else backoff)
        raise ScrapeHttpError(f"{method} {url} failed after {attempts} attempts: {last_problem}")

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)
