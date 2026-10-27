from urllib.parse import parse_qs

import httpx

from scraping.config import ScrapeSettings
from scraping.http import PoliteClient


class FakeTime:
    def __init__(self):
        self.now = 0.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def fast_settings(**overrides) -> ScrapeSettings:
    values = {"scrape_min_interval_seconds": 0.0, "scrape_max_retries": 1}
    values.update(overrides)
    return ScrapeSettings(**values)


def sebi_transport(
    pages: list[str],
    post_status: int = 200,
    get_status: int = 200,
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            if get_status != 200:
                return httpx.Response(get_status, text="unavailable")
            return httpx.Response(200, text=pages[0], headers={"Set-Cookie": "JSESSIONID=abc; Path=/"})
        if post_status != 200:
            return httpx.Response(post_status, text="unavailable")
        form = parse_qs(request.content.decode())
        index = int(form["doDirect"][0])
        if request.headers.get("referer") is None or "JSESSIONID=abc" not in request.headers.get(
            "cookie", ""
        ):
            return httpx.Response(530, text="session required")
        return httpx.Response(200, text=pages[index] if index < len(pages) else "")

    return httpx.MockTransport(handler)


def sebi_client(pages: list[str], **kwargs) -> PoliteClient:
    async def no_sleep(_: float) -> None:
        return None

    return PoliteClient(fast_settings(), transport=sebi_transport(pages, **kwargs), sleep=no_sleep)


def amfi_transport(
    rows_by_city: dict[str, list[dict]],
    cities: list[str],
    page_size: int = 50,
    api_status: int = 200,
    locate_status: int = 200,
) -> httpx.MockTransport:
    from tests.fixtures.generate_amfi_fixtures import render_api_page, render_locate_page

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/locate-distributor":
            if locate_status != 200:
                return httpx.Response(locate_status, text="unavailable")
            return httpx.Response(200, text=render_locate_page(cities))
        if api_status != 200:
            return httpx.Response(api_status, text="unavailable")
        params = request.url.params
        city = params["city"]
        payload = render_api_page(rows_by_city, city, int(params["page"]), page_size)
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def amfi_client(rows_by_city: dict[str, list[dict]], cities: list[str], **kwargs) -> PoliteClient:
    async def no_sleep(_: float) -> None:
        return None

    return PoliteClient(
        fast_settings(), transport=amfi_transport(rows_by_city, cities, **kwargs), sleep=no_sleep
    )
