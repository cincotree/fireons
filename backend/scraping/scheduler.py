import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from scraping.config import ScrapeSettings, get_scrape_settings
from scraping.runner import run_source
from scraping.sources import SOURCES
from scraping.types import RunAlreadyInProgress, RunTrigger

logger = logging.getLogger("scraping.scheduler")

JOB_ID = "scrape-all-sources"


async def run_all_sources() -> None:
    for key in sorted(SOURCES):
        try:
            summary = await run_source(key, RunTrigger.SCHEDULED)
            logger.info(
                "source=%s status=%s seen=%s inserted=%s updated=%s unchanged=%s delisted=%s",
                key,
                summary.status.value,
                summary.records_seen,
                summary.inserted,
                summary.updated,
                summary.unchanged,
                summary.marked_delisted,
            )
        except RunAlreadyInProgress:
            logger.warning("source=%s skipped: a run is already in progress", key)
        except Exception:
            logger.exception("source=%s run crashed", key)


def build_scheduler(settings: ScrapeSettings | None = None) -> AsyncIOScheduler:
    settings = settings or get_scrape_settings()
    scheduler = AsyncIOScheduler(timezone=settings.scrape_schedule_timezone)
    scheduler.add_job(
        run_all_sources,
        CronTrigger.from_crontab(
            settings.scrape_schedule_cron, timezone=settings.scrape_schedule_timezone
        ),
        id=JOB_ID,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    return scheduler


async def run_worker() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    job = scheduler.get_job(JOB_ID)
    logger.info("scheduler started; next run at %s", job.next_run_time if job else None)
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()
