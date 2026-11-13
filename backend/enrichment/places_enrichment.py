import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select

from database.models import DataSource, FinancialProfessional, ProfessionalRegistration, WebsiteLookup
from database.session import session_context
from enrichment import tavily
from enrichment.domains import domain_from_url, is_public_firm_domain
from enrichment.places import UsageLedger
from enrichment.runner import register_websites
from enrichment.website_finder import (
    DEFAULT_LEDGER_PATH,
    FOUND,
    MAX_SEARCH_CANDIDATES,
    METHOD_SEARCH,
    NOT_FOUND,
    _record,
    verified_domain,
)
from enrichment.website_match import clean_name, distinctive_tokens, is_directory_domain
from scraping.config import ScrapeSettings, get_scrape_settings
from scraping.http import PoliteClient
from scraping.normalize import classify_kind, collapse_whitespace, normalize_name
from scraping.sources.google_places import DEFINITION, read_place_rows

logger = logging.getLogger("enrichment.places_enrichment")

MAX_TITLE_LENGTH = 300
TITLE_SEPARATORS = re.compile(r"\s*\|\s*|\s+[-\u2013\u2014:]\s+")
LEGAL_TITLE = re.compile(r"\b(advocates?|lawyers?|law firm|legal)\b", re.IGNORECASE)
GENERIC_SEGMENTS = {"home", "homepage", "welcome", "index", "contact", "contact us", "about", "about us", "services"}


@dataclass
class PlacesEnrichmentSummary:
    rows_in_file: int = 0
    already_done: int = 0
    not_imported: int = 0
    enriched: int = 0
    listing_only: int = 0
    searches_made: int = 0
    searches_left_today: int = 0
    stopped_reason: str = "finished"


def best_title(title: str, name: str, city: str = "") -> str | None:
    if LEGAL_TITLE.search(title):
        return None
    city_words = set(distinctive_tokens(city)) | {word.lower() for word in re.findall(r"[A-Za-z0-9]+", city)}
    wanted = set(distinctive_tokens(name)) - city_words
    if not wanted:
        return None
    needed = math.ceil(len(wanted) / 2)
    best: tuple[int, str] | None = None
    for segment in TITLE_SEPARATORS.split(title):
        segment = collapse_whitespace(segment)
        if not segment or segment.lower() in GENERIC_SEGMENTS:
            continue
        overlap = len(wanted & (set(distinctive_tokens(segment)) - city_words))
        if overlap >= needed and (best is None or overlap > best[0]):
            best = (overlap, segment)
    return best[1][:MAX_TITLE_LENGTH] if best else None


async def _pending_rows(rows: list[dict]) -> tuple[list[tuple[dict, str]], int, int]:
    numbers = {f"GP-{row['place_id'].strip()}": row for row in rows}
    query = (
        select(ProfessionalRegistration.registration_number, ProfessionalRegistration.professional_id)
        .join(DataSource, DataSource.id == ProfessionalRegistration.source_id)
        .where(DataSource.key == DEFINITION.key, ProfessionalRegistration.registration_number.in_(list(numbers)))
    )
    done = select(WebsiteLookup.professional_id)
    async with session_context() as session:
        imported = {number: professional_id for number, professional_id in (await session.execute(query)).all()}
        finished = set(await session.scalars(done))
    pending = [(numbers[number], pid) for number, pid in imported.items() if pid not in finished]
    pending.sort(key=lambda item: item[0]["place_id"])
    return pending, len(numbers) - len(imported), len(imported) - len(pending)


async def _store_details(professional_id: str, title: str) -> None:
    async with session_context() as session:
        professional = await session.get(FinancialProfessional, professional_id)
        registration = await session.scalar(
            select(ProfessionalRegistration).where(ProfessionalRegistration.professional_id == professional_id)
        )
        professional.display_name = title
        professional.name_normalized = normalize_name(title)
        professional.kind = classify_kind(title).value
        registration.attributes = {**registration.attributes, "web_enriched": True}


async def _find_match(
    results: list[tavily.SearchResult], name: str, city: str, client: PoliteClient, settings: ScrapeSettings
) -> tuple[str, str] | None:
    seen: list[str] = []
    for result in results:
        domain = domain_from_url(result.url)
        if not domain or not is_public_firm_domain(domain) or is_directory_domain(domain) or domain in seen:
            continue
        seen.append(domain)
        if len(seen) > MAX_SEARCH_CANDIDATES:
            break
        title = best_title(result.title, name, city)
        if title and await verified_domain(domain, name, city, client, settings):
            return domain, title
    return None


async def enrich_places(
    csv_path: Path,
    client: PoliteClient | None = None,
    settings: ScrapeSettings | None = None,
    limit: int | None = None,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    tavily_transport: httpx.AsyncBaseTransport | None = None,
    now: datetime | None = None,
) -> PlacesEnrichmentSummary:
    settings = settings or get_scrape_settings()
    now = now or datetime.now(timezone.utc)
    summary = PlacesEnrichmentSummary()
    rows = read_place_rows(csv_path)
    summary.rows_in_file = len(rows)
    pending, summary.not_imported, summary.already_done = await _pending_rows(rows)
    if limit:
        pending = pending[:limit]
    if not settings.tavily_api_key:
        summary.stopped_reason = "TAVILY_API_KEY is not set"
        return summary
    ledger = UsageLedger(ledger_path, settings.website_search_daily_limit, settings.website_search_monthly_limit)
    await register_websites(settings)
    owns_client = client is None
    http_client = client or PoliteClient(settings.model_copy(update={"scrape_max_retries": 1}))
    try:
        for row, professional_id in pending:
            if ledger.remaining(now) <= 0:
                summary.stopped_reason = "daily or monthly search limit reached"
                break
            name = collapse_whitespace(row.get("name")) or ""
            city = collapse_whitespace(row.get("searched_city")) or ""
            ledger.record_call(now)
            summary.searches_made += 1
            try:
                results = await tavily.search_results(
                    settings.tavily_api_key, f"{clean_name(name)} {city}", transport=tavily_transport
                )
            except tavily.QuotaExhausted:
                summary.stopped_reason = "Tavily quota exhausted"
                break
            except tavily.TavilyError as exc:
                summary.stopped_reason = str(exc)
                break
            match = await _find_match(results, name, city, http_client, settings) if name and city else None
            if match:
                domain, title = match
                await _store_details(professional_id, title)
                await _record(professional_id, FOUND, METHOD_SEARCH, domain, now)
                summary.enriched += 1
            else:
                await _record(professional_id, NOT_FOUND, METHOD_SEARCH, None, now)
                summary.listing_only += 1
    finally:
        if owns_client:
            await http_client.__aexit__(None, None, None)
    summary.searches_left_today = ledger.remaining(now)
    return summary
