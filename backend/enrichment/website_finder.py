import asyncio
import logging
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.models import (
    DataSource,
    FinancialProfessional,
    ProfessionalRegistration,
    ProfessionalWebsite,
    WebsiteLookup,
)
from database.session import session_context
from enrichment import tavily
from enrichment.crawler import _fetch_html, _robots
from enrichment.domains import domain_from_url, is_public_firm_domain
from enrichment.places import UsageLedger
from enrichment.runner import PENDING, _add_website, register_websites
from enrichment.website_match import (
    clean_name,
    guess_domains,
    index_register_domains,
    is_directory_domain,
    name_key,
    page_matches,
)
from scraping.config import ScrapeSettings, get_scrape_settings
from scraping.http import PoliteClient
from scraping.types import ScrapeHttpError

logger = logging.getLogger("enrichment.website_finder")

FOUND = "found"
NEEDS_SEARCH = "needs_search"
NOT_FOUND = "not_found"
METHOD_REGISTER = "register_match"
METHOD_GUESS = "domain_guess"
METHOD_SEARCH = "web_search"
DNS_TIMEOUT_SECONDS = 3.0
MAX_SEARCH_CANDIDATES = 3
DEFAULT_LEDGER_PATH = Path("exports/tavily_usage.json")

Resolver = Callable[[str], Awaitable[bool]]


@dataclass
class FinderSummary:
    rows_considered: int = 0
    found_by_register: int = 0
    found_by_guess: int = 0
    found_by_search: int = 0
    not_found: int = 0
    left_for_search: int = 0
    searches_made: int = 0
    searches_left_today: int = 0
    stopped_reason: str = "finished"


async def resolves(domain: str) -> bool:
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(loop.getaddrinfo(domain, 443, type=socket.SOCK_STREAM), DNS_TIMEOUT_SECONDS)
    except (OSError, asyncio.TimeoutError):
        return False
    return True


async def _homepage(domain: str, client: PoliteClient, settings: ScrapeSettings) -> tuple[str, str] | None:
    for scheme in ("https", "http"):
        origin = f"{scheme}://{domain}"
        try:
            robots = await _robots(client, origin)
            if robots is None or not robots.can_fetch(settings.scrape_user_agent, f"{origin}/"):
                continue
            return await _fetch_html(client, f"{origin}/", settings.nri_max_page_bytes)
        except (ScrapeHttpError, httpx.HTTPError):
            continue
    return None


async def verified_domain(
    domain: str, name: str, city: str, client: PoliteClient, settings: ScrapeSettings
) -> bool:
    home = await _homepage(domain, client, settings)
    return home is not None and page_matches(name, city, home[1])


async def _load_candidates(limit: int | None, search_only: bool) -> list[tuple[str, str, str]]:
    has_site = select(ProfessionalWebsite.professional_id)
    lookups = select(WebsiteLookup.professional_id)
    query = (
        select(
            FinancialProfessional.id,
            FinancialProfessional.display_name,
            func.max(ProfessionalRegistration.city),
        )
        .join(ProfessionalRegistration, ProfessionalRegistration.professional_id == FinancialProfessional.id)
        .join(DataSource, DataSource.id == ProfessionalRegistration.source_id)
        .where(
            DataSource.verification_level == "unverified",
            DataSource.key != "google_places",
            ProfessionalRegistration.status != "delisted",
            ProfessionalRegistration.city.is_not(None),
            ProfessionalRegistration.attributes["website"].astext.is_(None),
            FinancialProfessional.id.not_in(has_site),
        )
        .group_by(FinancialProfessional.id, FinancialProfessional.display_name)
        .order_by(FinancialProfessional.display_name)
    )
    if search_only:
        query = query.where(
            FinancialProfessional.id.in_(select(WebsiteLookup.professional_id).where(WebsiteLookup.status == NEEDS_SEARCH))
        )
    else:
        query = query.where(FinancialProfessional.id.not_in(lookups))
        if limit:
            query = query.limit(limit)
    async with session_context() as session:
        return [(row[0], row[1], row[2]) for row in (await session.execute(query)).all()]


async def _register_index() -> dict:
    query = (
        select(ProfessionalWebsite.professional_id, FinancialProfessional.display_name, ProfessionalRegistration.city, ProfessionalWebsite.domain)
        .join(FinancialProfessional, FinancialProfessional.id == ProfessionalWebsite.professional_id)
        .join(ProfessionalRegistration, ProfessionalRegistration.professional_id == FinancialProfessional.id)
        .join(DataSource, DataSource.id == ProfessionalRegistration.source_id)
        .where(DataSource.verification_level == "verified")
    )
    async with session_context() as session:
        rows = [tuple(row) for row in (await session.execute(query)).all()]
    return index_register_domains(rows)


async def _record(professional_id: str, status: str, method: str | None, domain: str | None, now: datetime) -> None:
    async with session_context() as session:
        statement = (
            pg_insert(WebsiteLookup)
            .values(professional_id=professional_id, status=status, method=method, domain=domain, last_attempt_at=now)
            .on_conflict_do_update(
                index_elements=["professional_id"],
                set_={"status": status, "method": method, "domain": domain, "last_attempt_at": now},
            )
        )
        await session.execute(statement)
        if status == FOUND and domain:
            await _add_website(session, professional_id, domain, f"https://{domain}/", method)


async def _free_pass(
    candidates: list[tuple[str, str, str]],
    client: PoliteClient,
    settings: ScrapeSettings,
    summary: FinderSummary,
    resolver: Resolver,
    now: datetime,
) -> None:
    index = await _register_index()
    for professional_id, name, city in candidates:
        summary.rows_considered += 1
        key = name_key(name, city)
        if key is None:
            await _record(professional_id, NOT_FOUND, None, None, now)
            summary.not_found += 1
            continue
        known = sorted(index.get(key, ()))
        if known:
            await _record(professional_id, FOUND, METHOD_REGISTER, known[0], now)
            summary.found_by_register += 1
            continue
        match = None
        for domain in guess_domains(name):
            if await resolver(domain) and await verified_domain(domain, name, city, client, settings):
                match = domain
                break
        if match:
            await _record(professional_id, FOUND, METHOD_GUESS, match, now)
            summary.found_by_guess += 1
        else:
            await _record(professional_id, NEEDS_SEARCH, None, None, now)
            summary.left_for_search += 1


async def _search_pass(
    candidates: list[tuple[str, str, str]],
    client: PoliteClient,
    settings: ScrapeSettings,
    summary: FinderSummary,
    ledger: UsageLedger,
    api_key: str,
    transport: httpx.AsyncBaseTransport | None,
    now: datetime,
) -> None:
    for professional_id, name, city in candidates:
        if ledger.remaining(now) <= 0:
            summary.stopped_reason = "daily or monthly search limit reached"
            break
        ledger.record_call(now)
        summary.searches_made += 1
        try:
            urls = await tavily.search(api_key, f"{clean_name(name)} {city}", transport=transport)
        except tavily.QuotaExhausted:
            summary.stopped_reason = "Tavily quota exhausted"
            break
        except tavily.TavilyError as exc:
            summary.stopped_reason = str(exc)
            break
        domains: list[str] = []
        for url in urls:
            domain = domain_from_url(url)
            if domain and is_public_firm_domain(domain) and not is_directory_domain(domain) and domain not in domains:
                domains.append(domain)
        match = None
        for domain in domains[:MAX_SEARCH_CANDIDATES]:
            if await verified_domain(domain, name, city, client, settings):
                match = domain
                break
        if match:
            await _record(professional_id, FOUND, METHOD_SEARCH, match, now)
            summary.found_by_search += 1
        else:
            await _record(professional_id, NOT_FOUND, METHOD_SEARCH, None, now)
            summary.not_found += 1


async def find_websites(
    client: PoliteClient | None = None,
    settings: ScrapeSettings | None = None,
    limit: int | None = None,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    search: bool = True,
    resolver: Resolver = resolves,
    tavily_transport: httpx.AsyncBaseTransport | None = None,
    now: datetime | None = None,
) -> FinderSummary:
    settings = settings or get_scrape_settings()
    now = now or datetime.now(timezone.utc)
    summary = FinderSummary()
    await register_websites(settings)
    owns_client = client is None
    http_client = client or PoliteClient(settings.model_copy(update={"scrape_max_retries": 1}))
    ledger = UsageLedger(ledger_path, settings.website_search_daily_limit, settings.website_search_monthly_limit)
    try:
        await _free_pass(await _load_candidates(limit, search_only=False), http_client, settings, summary, resolver, now)
        if search and settings.tavily_api_key:
            pending = await _load_candidates(None, search_only=True)
            await _search_pass(
                pending, http_client, settings, summary, ledger, settings.tavily_api_key, tavily_transport, now
            )
        elif search:
            summary.stopped_reason = "TAVILY_API_KEY is not set, search step skipped"
    finally:
        if owns_client:
            await http_client.__aexit__(None, None, None)
    summary.left_for_search = len(await _load_candidates(None, search_only=True))
    summary.searches_left_today = ledger.remaining(now)
    return summary
