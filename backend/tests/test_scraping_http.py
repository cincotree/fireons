import httpx
import pytest

from scraping.http import PoliteClient
from scraping.types import ScrapeHttpError
from tests.scraping_helpers import FakeTime, fast_settings


def build_client(handler, fake: FakeTime, **settings) -> PoliteClient:
    return PoliteClient(
        fast_settings(scrape_min_interval_seconds=3.0, scrape_max_retries=3, **settings),
        transport=httpx.MockTransport(handler),
        sleep=fake.sleep,
        clock=fake.clock,
    )


async def test_requests_are_spaced_by_the_minimum_interval():
    fake = FakeTime()
    starts: list[float] = []

    def handler(request):
        starts.append(fake.now)
        return httpx.Response(200, text="ok")

    async with build_client(handler, fake) as client:
        for _ in range(4):
            await client.get("https://example.test/")

    gaps = [later - earlier for earlier, later in zip(starts, starts[1:])]
    assert len(starts) == 4
    assert all(gap >= 3.0 for gap in gaps)


async def test_retries_retryable_statuses_then_succeeds():
    fake = FakeTime()
    statuses = iter([530, 503, 200])
    starts: list[float] = []

    def handler(request):
        starts.append(fake.now)
        return httpx.Response(next(statuses), text="body")

    async with build_client(handler, fake) as client:
        response = await client.get("https://example.test/")

    assert response.status_code == 200
    assert client.request_count == 3
    assert all(later - earlier >= 3.0 for earlier, later in zip(starts, starts[1:]))


async def test_retry_after_header_is_honoured():
    fake = FakeTime()
    responses = iter([httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200)])

    async with build_client(lambda request: next(responses), fake) as client:
        await client.get("https://example.test/")

    assert 7.0 in fake.slept


async def test_gives_up_after_max_retries_with_clear_error():
    fake = FakeTime()

    async with build_client(lambda request: httpx.Response(530), fake) as client:
        with pytest.raises(ScrapeHttpError, match="failed after 4 attempts"):
            await client.get("https://example.test/")

    assert client.request_count == 4


async def test_non_retryable_status_fails_immediately():
    fake = FakeTime()

    async with build_client(lambda request: httpx.Response(404), fake) as client:
        with pytest.raises(ScrapeHttpError, match="404"):
            await client.get("https://example.test/")

    assert client.request_count == 1


async def test_transport_errors_are_retried():
    fake = FakeTime()
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200)

    async with build_client(handler, fake) as client:
        response = await client.get("https://example.test/")

    assert response.status_code == 200
    assert calls["n"] == 2


async def test_cookies_from_first_response_are_sent_on_later_requests():
    fake = FakeTime()
    seen_cookies: list[str] = []

    def handler(request):
        seen_cookies.append(request.headers.get("cookie", ""))
        return httpx.Response(200, headers={"Set-Cookie": "JSESSIONID=abc; Path=/"})

    async with build_client(handler, fake) as client:
        await client.get("https://example.test/")
        await client.post("https://example.test/ajax", data={"a": "1"})

    assert seen_cookies[0] == ""
    assert "JSESSIONID=abc" in seen_cookies[1]


async def test_user_agent_identifies_the_scraper():
    fake = FakeTime()
    agents: list[str] = []

    def handler(request):
        agents.append(request.headers["user-agent"])
        return httpx.Response(200)

    async with build_client(handler, fake, scrape_user_agent="Fireons-Test/9") as client:
        await client.get("https://example.test/")

    assert agents == ["Fireons-Test/9"]
