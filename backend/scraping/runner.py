import logging
import zlib
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import text, update

from database.models import DataSource, ScrapeRun
from database.session import get_engine, session_context
from scraping.config import ScrapeSettings, get_scrape_settings
from scraping.http import PoliteClient
from scraping.sources import get_source
from scraping.sources.base import Source
from scraping.store import ensure_data_source, mark_unseen_registrations, upsert_registrations
from scraping.types import (
    RunAlreadyInProgress,
    RunStatus,
    RunTrigger,
    ScrapedRegistration,
)


@dataclass
class RunSummary:
    run_id: str
    status: RunStatus
    expected_total: int | None
    pages_fetched: int
    records_seen: int
    inserted: int
    updated: int
    unchanged: int
    parse_errors: int
    marked_delisted: int
    error: str | None


logger = logging.getLogger("scraping.runner")


def _lock_key(source_key: str) -> int:
    return zlib.crc32(f"scrape:{source_key}".encode("utf-8"))


async def run_source(
    source_key: str,
    trigger: RunTrigger = RunTrigger.MANUAL,
    client: PoliteClient | None = None,
    settings: ScrapeSettings | None = None,
    today: date | None = None,
) -> RunSummary:
    settings = settings or get_scrape_settings()
    source = get_source(source_key)
    lock_connection = await get_engine().connect()
    try:
        acquired = await lock_connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": _lock_key(source_key)}
        )
        await lock_connection.commit()
        if not acquired:
            raise RunAlreadyInProgress(f"A scrape for {source_key} is already running")
        try:
            return await _execute(source, trigger, client, settings, today or date.today())
        finally:
            await lock_connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": _lock_key(source_key)}
            )
            await lock_connection.commit()
    finally:
        await lock_connection.close()


async def _execute(
    source: Source,
    trigger: RunTrigger,
    client: PoliteClient | None,
    settings: ScrapeSettings,
    today: date,
) -> RunSummary:
    started_at = datetime.now(timezone.utc)
    async with session_context() as session:
        data_source = await ensure_data_source(session, source.definition)
        await session.execute(
            update(ScrapeRun)
            .where(ScrapeRun.source_id == data_source.id, ScrapeRun.status == RunStatus.RUNNING.value)
            .values(
                status=RunStatus.FAILED.value,
                finished_at=started_at,
                error="Interrupted before completion",
            )
        )
        run = ScrapeRun(
            source_id=data_source.id,
            trigger=trigger.value,
            status=RunStatus.RUNNING.value,
            started_at=started_at,
        )
        session.add(run)
        await session.commit()
        run_id = run.id
        source_id = data_source.id

    owns_client = client is None
    http_client = client or PoliteClient(settings)
    summary = RunSummary(run_id, RunStatus.RUNNING, None, 0, 0, 0, 0, 0, 0, 0, None)
    seen_numbers: set[str] = set()
    try:
        async for page in source.fetch_pages(http_client):
            summary.pages_fetched += 1
            summary.parse_errors += page.parse_errors
            if page.expected_total is not None:
                summary.expected_total = page.expected_total
            fresh = _dedupe(page.records, seen_numbers)
            summary.records_seen += len(fresh)
            async with session_context() as session:
                data_source = await session.get(DataSource, source_id)
                counts = await upsert_registrations(
                    session, data_source, run_id, fresh, datetime.now(timezone.utc), today
                )
                await session.commit()
            summary.inserted += counts.inserted
            summary.updated += counts.updated
            summary.unchanged += counts.unchanged
        summary.status = _final_status(summary, settings)
    except Exception as exc:
        summary.error = f"{type(exc).__name__}: {exc}"
        summary.status = RunStatus.PARTIAL if summary.records_seen else RunStatus.FAILED
    finally:
        if owns_client:
            await http_client.__aexit__(None, None, None)

    async with session_context() as session:
        if summary.status == RunStatus.SUCCEEDED:
            data_source = await session.get(DataSource, source_id)
            summary.marked_delisted = await mark_unseen_registrations(
                session, data_source, started_at, settings.scrape_delist_after_missed_runs
            )
        await session.execute(
            update(ScrapeRun)
            .where(ScrapeRun.id == run_id)
            .values(
                status=summary.status.value,
                finished_at=datetime.now(timezone.utc),
                expected_total=summary.expected_total,
                pages_fetched=summary.pages_fetched,
                records_seen=summary.records_seen,
                inserted=summary.inserted,
                updated=summary.updated,
                unchanged=summary.unchanged,
                parse_errors=summary.parse_errors,
                marked_delisted=summary.marked_delisted,
                error=summary.error,
            )
        )
        await session.commit()
    return summary


def _dedupe(records: list[ScrapedRegistration], seen: set[str]) -> list[ScrapedRegistration]:
    fresh = []
    for record in records:
        if record.registration_number in seen:
            logger.warning("duplicate registration in listing skipped: %s", record.registration_number)
            continue
        seen.add(record.registration_number)
        fresh.append(record)
    return fresh


def _final_status(summary: RunSummary, settings: ScrapeSettings) -> RunStatus:
    if summary.parse_errors or summary.expected_total is None:
        return RunStatus.PARTIAL
    if summary.records_seen < summary.expected_total * settings.scrape_completeness_ratio:
        return RunStatus.PARTIAL
    return RunStatus.SUCCEEDED
