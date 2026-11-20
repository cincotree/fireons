import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from enrichment.signals import DetectedSignal, detect_signals
from scraping.config import ScrapeSettings
from scraping.http import PoliteClient
from scraping.types import ScrapeHttpError



logger = logging.getLogger("enrichment.crawler")

PRIORITY_LINK_PATTERN = re.compile(r"nri|non[\s-]*resident|overseas|abroad|global|international", re.IGNORECASE)
SECONDARY_LINK_PATTERN = re.compile(r"service|invest|wealth|advis|mutual|about|product|solution", re.IGNORECASE)

CHECKED = "checked"
UNREACHABLE = "unreachable"
BLOCKED_BY_ROBOTS = "blocked_by_robots"


@dataclass
class SiteResult:
    status: str
    url: str
    pages_checked: int = 0
    error: str | None = None
    signals: list[DetectedSignal] = field(default_factory=list)


def _same_site(host: str, other: str) -> bool:
    def strip(value: str) -> str:
        return value.lower().removeprefix("www.")

    return strip(host) == strip(other)


def _candidate_links(html: str, base_url: str, limit: int) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    base_host = urlparse(base_url).hostname or ""
    scored: dict[str, int] = {}
    for anchor in soup.find_all("a", href=True):
        target = urljoin(base_url, anchor["href"]).split("#")[0]
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or not _same_site(parsed.hostname or "", base_host):
            continue
        if parsed.path in {"", "/"} or re.search(r"\.(pdf|jpe?g|png|gif|zip|docx?|xlsx?|mp4)$", parsed.path, re.I):
            continue
        label = f"{anchor.get_text(' ')} {parsed.path}"
        if PRIORITY_LINK_PATTERN.search(label):
            score = 2
        elif SECONDARY_LINK_PATTERN.search(label):
            score = 1
        else:
            continue
        scored[target] = max(scored.get(target, 0), score)
    ordered = sorted(scored, key=lambda url: (-scored[url], len(url)))
    return ordered[:limit]


def _dedupe_across_pages(signals: list[DetectedSignal]) -> list[DetectedSignal]:
    rank = {"high": 0, "medium": 1, "low": 2}
    best: dict[tuple[str, str], DetectedSignal] = {}
    for signal in signals:
        key = (signal.signal_type.value, signal.text_hash)
        current = best.get(key)
        if current is None or rank[signal.confidence.value] < rank[current.confidence.value]:
            best[key] = signal
    return list(best.values())


async def _robots(client: PoliteClient, origin: str) -> RobotFileParser | None:
    parser = RobotFileParser()
    try:
        response = await client.get(f"{origin}/robots.txt")
    except ScrapeHttpError as exc:
        if "returned 4" in str(exc):
            parser.parse([])
            return parser
        return None
    parser.parse(response.text.splitlines())
    return parser


async def _fetch_html(client: PoliteClient, url: str, max_bytes: int) -> tuple[str, str] | None:
    response = await client.get(url)
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type.lower():
        return None
    return str(response.url), response.text[:max_bytes]


async def check_site(domain: str, client: PoliteClient, settings: ScrapeSettings) -> SiteResult:
    user_agent = settings.scrape_user_agent
    last_error = "no attempt made"
    for scheme in ("https", "http"):
        origin = f"{scheme}://{domain}"
        try:
            robots = await _robots(client, origin)
        except httpx.HTTPError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue
        if robots is None:
            last_error = "robots.txt unavailable"
            continue
        if not robots.can_fetch(user_agent, f"{origin}/"):
            return SiteResult(BLOCKED_BY_ROBOTS, f"{origin}/")
        try:
            home = await _fetch_html(client, f"{origin}/", settings.nri_max_page_bytes)
        except ScrapeHttpError as exc:
            last_error = str(exc)
            continue
        if home is None:
            return SiteResult(UNREACHABLE, f"{origin}/", error="homepage is not HTML")
        return await _crawl(client, robots, home, origin, settings)
    return SiteResult(UNREACHABLE, f"https://{domain}/", error=last_error)


async def _crawl(
    client: PoliteClient,
    robots: RobotFileParser,
    home: tuple[str, str],
    origin: str,
    settings: ScrapeSettings,
) -> SiteResult:
    home_url, home_html = home
    result = SiteResult(CHECKED, home_url, pages_checked=1)
    result.signals.extend(detect_signals(home_url, home_html))
    extra = max(settings.nri_max_pages_per_site - 1, 0)
    for link in _candidate_links(home_html, home_url, extra):
        if not robots.can_fetch(settings.scrape_user_agent, link):
            continue
        try:
            page = await _fetch_html(client, link, settings.nri_max_page_bytes)
        except ScrapeHttpError as exc:
            logger.info("skipping %s: %s", link, exc)
            continue
        if page is None:
            continue
        result.pages_checked += 1
        result.signals.extend(detect_signals(page[0], page[1]))
    result.signals = _dedupe_across_pages(result.signals)
    return result
