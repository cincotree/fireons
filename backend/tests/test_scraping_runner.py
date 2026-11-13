import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import ProfessionalRegistration, RegistrationVersion, ScrapeRun
from scraping.runner import _lock_key, run_source
from scraping.types import RegistrationStatus, RunAlreadyInProgress, RunStatus
from tests.fixtures.generate_sebi_fixtures import (
    BROKEN_RECORD,
    GOOD_RECORDS,
    SAMPLE_RECORDS,
    build_pages,
)
from tests.scraping_helpers import fast_settings, sebi_client


@pytest_asyncio.fixture(autouse=True)
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


async def scrape(records, **client_kwargs):
    async with sebi_client(build_pages(records), **client_kwargs) as client:
        return await run_source("sebi_ria", client=client, settings=fast_settings())


async def registrations(engine):
    async with AsyncSession(engine) as session:
        rows = (await session.scalars(select(ProfessionalRegistration))).all()
        return {r.registration_number: r for r in rows}


async def scalar(engine, query):
    async with AsyncSession(engine) as session:
        return await session.scalar(query)


async def test_full_run_stores_everything_and_records_the_run(engine):
    summary = await scrape(GOOD_RECORDS)

    assert summary.status == RunStatus.SUCCEEDED
    assert (summary.pages_fetched, summary.records_seen, summary.inserted) == (2, 6, 6)
    assert summary.expected_total == 6
    assert len(await registrations(engine)) == 6
    run_row = await scalar(engine, select(ScrapeRun))
    assert run_row.status == "succeeded"
    assert run_row.records_seen == 6
    assert run_row.finished_at is not None


async def test_second_identical_run_changes_nothing(engine):
    await scrape(GOOD_RECORDS)

    summary = await scrape(GOOD_RECORDS)

    assert summary.status == RunStatus.SUCCEEDED
    assert (summary.inserted, summary.updated, summary.unchanged) == (0, 0, 6)
    assert await scalar(engine, select(func.count()).select_from(RegistrationVersion)) == 6
    assert await scalar(engine, select(func.count()).select_from(ScrapeRun)) == 2


async def test_changed_upstream_record_is_updated_and_versioned(engine):
    await scrape(GOOD_RECORDS)
    changed = [dict(record) for record in GOOD_RECORDS]
    changed[0]["phone"] = "919876543210"

    summary = await scrape(changed)

    assert (summary.updated, summary.unchanged) == (1, 5)
    assert (await registrations(engine))["INA000000001"].phone == "919876543210"
    assert await scalar(engine, select(func.count()).select_from(RegistrationVersion)) == 7


async def test_duplicates_are_collapsed_and_parse_errors_make_the_run_partial(engine):
    summary = await scrape(SAMPLE_RECORDS)

    assert summary.records_seen == 6
    assert summary.inserted == 6
    assert summary.parse_errors == 1
    assert summary.status == RunStatus.PARTIAL


async def test_unlisted_registration_is_delisted_after_two_complete_runs(engine):
    await scrape(GOOD_RECORDS)
    remaining = GOOD_RECORDS[:-1]

    first = await scrape(remaining)
    second = await scrape(remaining)

    leaver = (await registrations(engine))["INA000000007"]
    assert first.marked_delisted == 0
    assert second.marked_delisted == 1
    assert leaver.status == RegistrationStatus.DELISTED.value


async def test_partial_runs_never_delist_anything(engine):
    await scrape(GOOD_RECORDS)
    with_broken = GOOD_RECORDS[:-1] + [BROKEN_RECORD]

    for _ in range(3):
        summary = await scrape(with_broken)
        assert summary.status == RunStatus.PARTIAL
        assert summary.marked_delisted == 0

    rows = await registrations(engine)
    assert all(row.status != RegistrationStatus.DELISTED.value for row in rows.values())
    assert rows["INA000000007"].missing_runs == 0


async def test_failure_mid_run_is_partial_and_protects_existing_data(engine):
    await scrape(GOOD_RECORDS)

    summary = await scrape(GOOD_RECORDS, post_status=503)

    assert summary.status == RunStatus.PARTIAL
    assert "failed after 2 attempts" in summary.error
    assert summary.marked_delisted == 0
    rows = await registrations(engine)
    assert len(rows) == 6
    assert all(row.missing_runs == 0 for row in rows.values())


async def test_failure_on_first_request_marks_run_failed(engine):
    summary = await scrape(GOOD_RECORDS, get_status=503)

    assert summary.status == RunStatus.FAILED
    assert summary.records_seen == 0
    run_row = await scalar(engine, select(ScrapeRun))
    assert run_row.status == "failed"
    assert run_row.error


async def test_second_concurrent_run_is_refused_by_the_advisory_lock(engine):
    async with engine.connect() as holder:
        await holder.execute(text("SELECT pg_advisory_lock(:key)"), {"key": _lock_key("sebi_ria")})
        with pytest.raises(RunAlreadyInProgress):
            await scrape(GOOD_RECORDS)
        await holder.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _lock_key("sebi_ria")})
        await holder.commit()

    summary = await scrape(GOOD_RECORDS)

    assert summary.status == RunStatus.SUCCEEDED


async def test_stale_running_rows_are_closed_out_by_the_next_run(engine):
    await scrape(GOOD_RECORDS)
    async with AsyncSession(engine) as session:
        first_run = await session.scalar(select(ScrapeRun))
        session.add(ScrapeRun(source_id=first_run.source_id, trigger="scheduled", status="running"))
        await session.commit()

    await scrape(GOOD_RECORDS)

    async with AsyncSession(engine) as session:
        statuses = [r.status for r in (await session.scalars(select(ScrapeRun))).all()]
    assert "running" not in statuses
    assert "failed" in statuses


async def test_unknown_source_key_is_rejected():
    with pytest.raises(KeyError, match="Unknown source"):
        await run_source("nope")
