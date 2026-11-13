from datetime import datetime

import pytest
from zoneinfo import ZoneInfo

from scraping.config import ScrapeSettings
from scraping.scheduler import JOB_ID, build_scheduler

IST = ZoneInfo("Asia/Kolkata")


def test_scheduler_registers_a_single_non_overlapping_job():
    job = build_scheduler(ScrapeSettings()).get_job(JOB_ID)

    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True


def test_default_schedule_fires_on_sunday_at_3am_india_time():
    job = build_scheduler(ScrapeSettings()).get_job(JOB_ID)
    now = datetime(2026, 10, 22, 12, 0, tzinfo=IST)

    fire_time = job.trigger.get_next_fire_time(None, now)

    assert fire_time.weekday() == 6
    assert (fire_time.hour, fire_time.minute) == (3, 0)
    assert fire_time.tzinfo is not None
    assert fire_time.utcoffset().total_seconds() == 5.5 * 3600


def test_schedule_is_configurable_through_settings():
    job = build_scheduler(ScrapeSettings(scrape_schedule_cron="30 6 * * mon")).get_job(JOB_ID)
    now = datetime(2026, 10, 22, 12, 0, tzinfo=IST)

    fire_time = job.trigger.get_next_fire_time(None, now)

    assert fire_time.weekday() == 0
    assert (fire_time.hour, fire_time.minute) == (6, 30)


def test_invalid_cron_expression_fails_fast():
    with pytest.raises(ValueError):
        build_scheduler(ScrapeSettings(scrape_schedule_cron="not a cron"))
