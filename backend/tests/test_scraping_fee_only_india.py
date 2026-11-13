import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import ProfessionalRegistration
from scraping.http import PoliteClient
from scraping.runner import run_source
from scraping.sources.fee_only_india import (
    FeeOnlyIndiaSource,
    clean_website,
    parse_listing_page,
    registration_number_for,
)
from scraping.types import ProfessionalKind, ProfessionType, RunStatus, ScrapeHttpError
from tests.fixtures.generate_fee_only_fixtures import PLANNERS, render_listing
from tests.scraping_helpers import fast_settings


@pytest_asyncio.fixture
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


def client_for(html: str | None = None, status: int = 200) -> PoliteClient:
    async def no_sleep(_: float) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=html if html is not None else render_listing())

    return PoliteClient(fast_settings(), transport=httpx.MockTransport(handler), sleep=no_sleep)


async def scrape(html: str | None = None, status: int = 200):
    async with client_for(html, status) as client:
        return await run_source("fee_only_india", client=client, settings=fast_settings())


def test_only_planner_cards_are_parsed_not_the_feature_blurbs():
    page = parse_listing_page(render_listing())

    assert [r.name for r in page.records] == ["Asha Fictional", "Ravi Imaginary", "Meera Placeholder"]
    assert page.expected_total == 3
    assert page.parse_errors == 0


def test_fields_are_normalized_and_tracking_parameters_removed():
    record = parse_listing_page(render_listing()).records[0]

    assert record.registration_number == "FOI-asha-fictional"
    assert record.profession_type == ProfessionType.FEE_ONLY_PLANNER
    assert record.kind == ProfessionalKind.INDIVIDUAL
    assert record.contact_person == "Asha Fictional"
    assert record.valid_until is None and record.city is None and record.email is None
    assert record.attributes == {
        "firm_name": "Sample Planning Studio",
        "website": "https://www.sampleplanning.example.com/",
        "languages": ["Hindi", "Tamil"],
        "membership": "Fee-Only India",
    }


def test_every_card_is_a_person_even_when_they_practise_under_a_firm_name():
    page = parse_listing_page(render_listing())

    assert {r.kind for r in page.records} == {ProfessionalKind.INDIVIDUAL}
    record = page.records[1]
    assert record.attributes["website"] == "https://raviplans.example.org/"


def test_footnote_in_the_firm_line_becomes_a_note():
    record = parse_listing_page(render_listing()).records[2]

    assert record.attributes["firm_name"] == "Placeholder Wealth"
    assert record.attributes["note"] == "Stopped taking new clients from Mar 1, 2024"
    assert record.attributes["website"] == "https://placeholderwealth.example.com/about/"


def test_card_without_a_name_counts_as_a_parse_error():
    page = parse_listing_page(render_listing([*PLANNERS, {"name": "", "firm": "Nameless Firm", "website": "https://n.example.com"}]))

    assert page.parse_errors == 1
    assert len(page.records) == 3
    assert page.expected_total == 4


def test_planner_without_website_or_languages_still_parses():
    page = parse_listing_page(render_listing([{"name": "Solo Planner", "firm": "Solo Planner"}]))

    assert page.records[0].attributes == {"firm_name": "Solo Planner", "membership": "Fee-Only India"}


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://a.example.com/?utm_source=x", "https://a.example.com/"),
        ("http://a.example.com/page?x=1", "http://a.example.com/page"),
        ("javascript:alert(1)", None),
        ("not a url", None),
        (None, None),
    ],
)
def test_clean_website(url, expected):
    assert clean_website(url) == expected


def test_registration_number_is_a_stable_slug_of_the_name():
    assert registration_number_for("S. R. Srinivasan") == "FOI-s-r-srinivasan"
    assert registration_number_for("Vishnu M") == "FOI-vishnu-m"


async def test_page_without_planner_cards_is_an_error_not_an_empty_success():
    async with client_for("<html><body>maintenance</body></html>") as client:
        with pytest.raises(ScrapeHttpError, match="layout"):
            [page async for page in FeeOnlyIndiaSource().fetch_pages(client)]


@pytest.mark.usefixtures("use_test_engine")
async def test_full_run_stores_every_planner_and_a_rerun_changes_nothing(engine):
    first = await scrape()
    second = await scrape()

    assert first.status == RunStatus.SUCCEEDED
    assert (first.records_seen, first.inserted, first.expected_total) == (3, 3, 3)
    assert (second.inserted, second.updated, second.unchanged) == (0, 0, 3)
    async with AsyncSession(engine) as session:
        rows = (await session.scalars(select(ProfessionalRegistration))).all()
    assert {r.profession_type for r in rows} == {"fee_only_planner"}
    assert {r.status for r in rows} == {"active"}


@pytest.mark.usefixtures("use_test_engine")
async def test_changed_website_is_recorded_as_an_update():
    await scrape()
    changed = [{**PLANNERS[0], "website": "https://new.example.com"}, *PLANNERS[1:]]

    summary = await scrape(render_listing(changed))

    assert (summary.updated, summary.unchanged) == (1, 2)


@pytest.mark.usefixtures("use_test_engine")
async def test_site_outage_fails_the_run_and_stores_nothing(engine):
    summary = await scrape(status=503)

    assert summary.status == RunStatus.FAILED
    async with AsyncSession(engine) as session:
        assert (await session.scalars(select(ProfessionalRegistration))).all() == []


@pytest.mark.usefixtures("use_test_engine")
async def test_unparseable_card_makes_the_run_partial_so_nobody_gets_delisted():
    summary = await scrape(render_listing([*PLANNERS, {"name": "", "firm": "Nameless", "website": "https://n.example.com"}]))

    assert summary.status == RunStatus.PARTIAL
    assert summary.inserted == 3
