import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import ProfessionalRegistration
from scraping.runner import run_source
from scraping.sources.sebi_research_analyst import LISTING_URL, SebiResearchAnalystSource
from scraping.sources.sebi_ria import parse_listing_page
from scraping.types import ProfessionType, RunStatus
from tests.fixtures.generate_sebi_fixtures import GOOD_RECORDS, build_pages
from tests.scraping_helpers import fast_settings, sebi_client


@pytest_asyncio.fixture
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


def analyst_pages(records):
    return [page.replace("INA", "INH") for page in build_pages(records)]


async def scrape(records=GOOD_RECORDS):
    async with sebi_client(analyst_pages(records)) as client:
        return await run_source("sebi_research_analyst", client=client, settings=fast_settings())


def test_research_analyst_numbers_are_accepted_and_adviser_numbers_rejected():
    source = SebiResearchAnalystSource()
    analyst_page = source._parse(analyst_pages(GOOD_RECORDS)[0])
    adviser_page = source._parse(build_pages(GOOD_RECORDS)[0])

    assert analyst_page.parse_errors == 0
    assert analyst_page.records[0].registration_number == "INH000000001"
    assert analyst_page.records[0].profession_type == ProfessionType.RESEARCH_ANALYST
    assert adviser_page.records == []
    assert adviser_page.parse_errors == analyst_page.parse_errors + len(analyst_page.records)


def test_listing_url_points_at_the_research_analyst_register():
    assert LISTING_URL.endswith("intmId=14")
    assert SebiResearchAnalystSource().listing_url == LISTING_URL
    assert parse_listing_page(analyst_pages(GOOD_RECORDS)[0]).records == []


@pytest.mark.usefixtures("use_test_engine")
async def test_full_run_stores_analysts_under_their_own_source(engine):
    summary = await scrape()

    assert summary.status == RunStatus.SUCCEEDED
    assert summary.inserted == len(GOOD_RECORDS)
    async with AsyncSession(engine) as session:
        rows = (await session.scalars(select(ProfessionalRegistration))).all()
    assert {r.profession_type for r in rows} == {"research_analyst"}
    assert {r.source_url for r in rows} == {LISTING_URL}
    assert all(r.registration_number.startswith("INH") for r in rows)


@pytest.mark.usefixtures("use_test_engine")
async def test_rerun_changes_nothing_and_adviser_numbers_make_the_run_partial():
    await scrape()
    again = await scrape()

    assert (again.inserted, again.updated) == (0, 0)
    async with sebi_client(build_pages(GOOD_RECORDS)) as client:
        wrong = await run_source("sebi_research_analyst", client=client, settings=fast_settings())
    assert wrong.status == RunStatus.PARTIAL
