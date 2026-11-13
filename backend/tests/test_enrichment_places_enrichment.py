from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import FinancialProfessional, ProfessionalRegistration, ProfessionalWebsite, WebsiteLookup
from enrichment.places_enrichment import enrich_places
from scraping.config import ScrapeSettings
from scraping.http import PoliteClient
from tests.scraping_helpers import fast_settings
from tests.test_enrichment_website_finder import firm_page, site_transport
from tests.test_scraping_google_places import load, row, write_csv

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


def listing(number: int, name: str, city: str = "Pune") -> dict:
    return row(number, name=name, searched_city=city)


def tavily_returning(results: list[dict], status: int = 200):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json={"results": results})

    transport = httpx.MockTransport(handler)
    transport.seen = seen
    return transport


def client_for(sites):
    async def no_sleep(_):
        return None

    return PoliteClient(fast_settings(), transport=site_transport(sites), sleep=no_sleep)


def settings(**overrides):
    return ScrapeSettings(scrape_min_interval_seconds=0.0, scrape_max_retries=1, tavily_api_key="key", **overrides)


async def run(csv_path, tmp_path, sites, search, **kwargs):
    client = client_for(sites)
    async with client:
        return await enrich_places(
            csv_path,
            client=client,
            settings=kwargs.pop("settings", settings()),
            ledger_path=tmp_path / "tavily.json",
            tavily_transport=search,
            now=NOW,
            **kwargs,
        )


async def registration(engine, place: str):
    async with AsyncSession(engine) as session:
        reg = await session.scalar(
            select(ProfessionalRegistration).where(ProfessionalRegistration.registration_number == f"GP-{place}")
        )
        professional = await session.get(FinancialProfessional, reg.professional_id)
        lookup = await session.scalar(select(WebsiteLookup).where(WebsiteLookup.professional_id == reg.professional_id))
        websites = (
            await session.scalars(select(ProfessionalWebsite).where(ProfessionalWebsite.professional_id == reg.professional_id))
        ).all()
        return reg, professional, lookup, websites


async def imported(tmp_path, rows):
    path = write_csv(tmp_path / "places.csv", rows)
    await load(path)
    return path


@pytest.mark.usefixtures("use_test_engine")
async def test_a_verified_match_stores_the_tavily_title_and_website_not_the_google_name(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Zed Quartz Advisers")])
    sites = {"zedquartz.net": {"/": firm_page("Zed Quartz Advisers", "Pune")}}
    search = tavily_returning([{"url": "https://zedquartz.net/about", "title": "Zed Quartz | Tax and Advisory, Pune"}])

    summary = await run(path, tmp_path, sites, search)

    reg, professional, lookup, websites = await registration(engine, "place-1")
    assert (summary.enriched, summary.listing_only, summary.searches_made) == (1, 0, 1)
    assert professional.display_name == "Zed Quartz | Tax and Advisory, Pune"
    assert "Zed Quartz Advisers" != professional.display_name
    assert reg.attributes == {"google_place_id": "place-1", "web_enriched": True}
    assert (lookup.status, lookup.method, lookup.domain) == ("found", "web_search", "zedquartz.net")
    assert [w.domain for w in websites] == ["zedquartz.net"]
    assert reg.source_url == "https://maps.example.test/1"


@pytest.mark.usefixtures("use_test_engine")
async def test_no_match_leaves_only_the_place_id_and_maps_link(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Zed Quartz Advisers")])
    sites = {"other.example.org": {"/": firm_page("Other Firm", "Delhi")}}
    search = tavily_returning([{"url": "https://other.example.org/", "title": "Other Firm"}])

    summary = await run(path, tmp_path, sites, search)

    reg, professional, lookup, websites = await registration(engine, "place-1")
    assert (summary.enriched, summary.listing_only) == (0, 1)
    assert professional.display_name == "Google Maps listing"
    assert reg.attributes == {"google_place_id": "place-1"}
    assert reg.source_url == "https://maps.example.test/1"
    assert lookup.status == "not_found"
    assert websites == []


@pytest.mark.usefixtures("use_test_engine")
async def test_directory_sites_and_untitled_results_are_not_used(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Zed Quartz Advisers")])
    sites = {
        "justdial.com": {"/": firm_page("Zed Quartz Advisers", "Pune")},
        "zedquartz.net": {"/": firm_page("Zed Quartz Advisers", "Pune")},
    }
    search = tavily_returning(
        [{"url": "https://www.justdial.com/zed", "title": "Zed Quartz on Justdial"}, {"url": "https://zedquartz.net/", "title": ""}]
    )

    summary = await run(path, tmp_path, sites, search)

    _, professional, _, _ = await registration(engine, "place-1")
    assert summary.enriched == 0
    assert professional.display_name == "Google Maps listing"


@pytest.mark.usefixtures("use_test_engine")
async def test_a_page_for_the_wrong_city_is_rejected(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Zed Quartz Advisers", city="Pune")])
    sites = {"zedquartz.net": {"/": firm_page("Zed Quartz Advisers", "Chennai")}}
    search = tavily_returning([{"url": "https://zedquartz.net/", "title": "Zed Quartz"}])

    summary = await run(path, tmp_path, sites, search)

    assert (summary.enriched, summary.listing_only) == (0, 1)


@pytest.mark.usefixtures("use_test_engine")
async def test_finished_listings_are_not_searched_again(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Zed Quartz Advisers")])
    search = tavily_returning([])
    await run(path, tmp_path, {}, search)

    again = await run(path, tmp_path, {}, search)

    assert again.already_done == 1
    assert again.searches_made == 0
    assert len(search.seen) == 1


@pytest.mark.usefixtures("use_test_engine")
async def test_the_daily_limit_stops_the_run_and_the_rest_waits(engine, tmp_path):
    path = await imported(
        tmp_path, [listing(1, "Alpha Quartz Advisers"), listing(2, "Beta Quartz Advisers"), listing(3, "Gamma Quartz Advisers")]
    )
    search = tavily_returning([])

    summary = await run(path, tmp_path, {}, search, settings=settings(website_search_daily_limit=2))

    assert summary.searches_made == 2
    assert "limit" in summary.stopped_reason
    assert (await registration(engine, "place-3"))[2] is None


@pytest.mark.usefixtures("use_test_engine")
async def test_limit_caps_the_listings_searched(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Alpha Quartz Advisers"), listing(2, "Beta Quartz Advisers")])

    summary = await run(path, tmp_path, {}, tavily_returning([]), limit=1)

    assert summary.searches_made == 1


@pytest.mark.usefixtures("use_test_engine")
async def test_a_tavily_quota_error_stops_without_marking_the_listing(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Zed Quartz Advisers")])

    summary = await run(path, tmp_path, {}, tavily_returning([], status=432))

    assert "Tavily" in summary.stopped_reason
    assert (await registration(engine, "place-1"))[2] is None


@pytest.mark.usefixtures("use_test_engine")
async def test_without_a_tavily_key_nothing_is_searched(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Zed Quartz Advisers")])
    search = tavily_returning([])

    summary = await run(path, tmp_path, {}, search, settings=ScrapeSettings(tavily_api_key=""))

    assert summary.stopped_reason == "TAVILY_API_KEY is not set"
    assert search.seen == []


@pytest.mark.usefixtures("use_test_engine")
async def test_rows_that_were_never_imported_are_skipped(engine, tmp_path):
    path = write_csv(tmp_path / "places.csv", [listing(1, "Zed Quartz Advisers")])
    search = tavily_returning([])

    summary = await run(path, tmp_path, {}, search)

    assert (summary.not_imported, summary.searches_made) == (1, 0)


@pytest.mark.usefixtures("use_test_engine")
async def test_reimporting_the_csv_does_not_undo_enrichment(engine, tmp_path):
    path = await imported(tmp_path, [listing(1, "Zed Quartz Advisers")])
    sites = {"zedquartz.net": {"/": firm_page("Zed Quartz Advisers", "Pune")}}
    await run(path, tmp_path, sites, tavily_returning([{"url": "https://zedquartz.net/", "title": "Zed Quartz Tax"}]))

    summary = await load(path)

    _, professional, _, _ = await registration(engine, "place-1")
    assert summary.inserted == summary.updated == 0
    assert professional.display_name == "Zed Quartz Tax"
