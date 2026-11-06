import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.models import NriSignal, ProfessionalRegistration, ProfessionalWebsite
from database.session import session_context
from enrichment.crawler import CHECKED, SiteResult, check_site
from enrichment.domains import candidate_domains, domain_from_url, is_public_firm_domain
from scraping.config import ScrapeSettings, get_scrape_settings
from scraping.http import PoliteClient

logger = logging.getLogger("enrichment.runner")

DERIVED_FROM_EMAIL = "email_domain"
DERIVED_FROM_LISTING = "source_listing"
PENDING = "pending"


@dataclass
class EnrichmentSummary:
    websites_known: int = 0
    websites_checked: int = 0
    unreachable: int = 0
    blocked_by_robots: int = 0
    crawl_errors: int = 0
    signals_found: int = 0
    signals_removed: int = 0


async def _add_website(session, professional_id: str, domain: str, url: str, derived_from: str) -> None:
    statement = (
        pg_insert(ProfessionalWebsite)
        .values(
            professional_id=professional_id,
            domain=domain,
            url=url,
            derived_from=derived_from,
            check_status=PENDING,
            pages_checked=0,
        )
        .on_conflict_do_nothing(constraint="uq_website_professional_domain")
    )
    await session.execute(statement)


async def register_websites(settings: ScrapeSettings) -> int:
    async with session_context() as session:
        rows = (
            await session.execute(
                select(ProfessionalRegistration.professional_id, ProfessionalRegistration.email).where(
                    ProfessionalRegistration.email.is_not(None),
                    ProfessionalRegistration.status != "delisted",
                )
            )
        ).all()
        emails: dict[str, list[str]] = {}
        for professional_id, email in rows:
            emails.setdefault(professional_id, []).append(email)
        for professional_id, domains in candidate_domains(emails, settings.nri_shared_domain_limit).items():
            for domain in domains:
                await _add_website(session, professional_id, domain, f"https://{domain}/", DERIVED_FROM_EMAIL)
        listed = (
            await session.execute(
                select(
                    ProfessionalRegistration.professional_id,
                    ProfessionalRegistration.attributes["website"].astext,
                ).where(
                    ProfessionalRegistration.attributes["website"].astext.is_not(None),
                    ProfessionalRegistration.status != "delisted",
                )
            )
        ).all()
        for professional_id, website in listed:
            domain = domain_from_url(website)
            if domain and is_public_firm_domain(domain):
                await _add_website(session, professional_id, domain, website, DERIVED_FROM_LISTING)
        count = len((await session.scalars(select(ProfessionalWebsite.id))).all())
    return count


async def _due_websites(settings: ScrapeSettings, now: datetime, limit: int | None) -> list[tuple[str, str]]:
    cutoff = now - timedelta(days=settings.nri_recheck_days)
    query = (
        select(ProfessionalWebsite.id, ProfessionalWebsite.domain)
        .where(
            or_(
                ProfessionalWebsite.last_checked_at.is_(None),
                ProfessionalWebsite.last_checked_at < cutoff,
            )
        )
        .order_by(ProfessionalWebsite.last_checked_at.asc().nulls_first(), ProfessionalWebsite.domain)
    )
    if limit:
        query = query.limit(limit)
    async with session_context() as session:
        return [(row.id, row.domain) for row in (await session.execute(query)).all()]


async def _store_result(website_id: str, result: SiteResult, now: datetime) -> tuple[int, int]:
    found = removed = 0
    async with session_context() as session:
        website = await session.get(ProfessionalWebsite, website_id)
        website.check_status = result.status
        website.url = result.url
        website.pages_checked = result.pages_checked
        website.error = result.error
        website.last_checked_at = now
        if result.status == CHECKED:
            seen_keys = set()
            for signal in result.signals:
                key = (signal.page_url, signal.signal_type.value, signal.text_hash)
                seen_keys.add(key)
                statement = (
                    pg_insert(NriSignal)
                    .values(
                        website_id=website.id,
                        professional_id=website.professional_id,
                        page_url=signal.page_url,
                        signal_type=signal.signal_type.value,
                        matched_text=signal.matched_text,
                        text_hash=signal.text_hash,
                        location=signal.location.value,
                        confidence=signal.confidence.value,
                        review_status=PENDING,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                    .on_conflict_do_update(
                        constraint="uq_signal_identity",
                        set_={
                            "matched_text": signal.matched_text,
                            "location": signal.location.value,
                            "confidence": signal.confidence.value,
                            "last_seen_at": now,
                        },
                    )
                )
                await session.execute(statement)
            found = len(seen_keys)
            stale = await session.execute(
                delete(NriSignal).where(
                    NriSignal.website_id == website.id,
                    NriSignal.review_status == PENDING,
                    NriSignal.last_seen_at < now,
                )
            )
            removed = stale.rowcount or 0
    return found, removed


async def enrich_nri(
    client: PoliteClient | None = None,
    settings: ScrapeSettings | None = None,
    limit: int | None = None,
    now: datetime | None = None,
) -> EnrichmentSummary:
    settings = settings or get_scrape_settings()
    now = now or datetime.now(timezone.utc)
    summary = EnrichmentSummary()
    summary.websites_known = await register_websites(settings)
    due = await _due_websites(settings, now, limit)
    owns_client = client is None
    http_client = client or PoliteClient(settings.model_copy(update={"scrape_max_retries": 1}))
    try:
        for website_id, domain in due:
            try:
                result = await check_site(domain, http_client, settings)
                found, removed = await _store_result(website_id, result, now)
            except Exception:
                logger.exception("enrichment failed for %s", domain)
                summary.crawl_errors += 1
                continue
            summary.websites_checked += 1
            summary.signals_found += found
            summary.signals_removed += removed
            if result.status == "unreachable":
                summary.unreachable += 1
            elif result.status == "blocked_by_robots":
                summary.blocked_by_robots += 1
    finally:
        if owns_client:
            await http_client.__aexit__(None, None, None)
    return summary
