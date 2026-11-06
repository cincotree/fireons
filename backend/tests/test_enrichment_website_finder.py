import json
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import (
    DataSource,
    FinancialProfessional,
    ProfessionalRegistration,
    ProfessionalWebsite,
    WebsiteLookup,
)
from enrichment import tavily
from enrichment.website_finder import find_websites
from enrichment.website_match import (
    clean_name,
    distinctive_tokens,
    guess_domains,
    is_directory_domain,
    page_matches,
)
from scraping.config import ScrapeSettings
from scraping.http import PoliteClient
from tests.scraping_helpers import fast_settings

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


def firm_page(name, city, extra="Chartered accountants and tax consultants."):
    return f"<html><head><title>{name}</title></head><body><h1>{name}</h1><p>{extra} Office in {city}.</p></body></html>"


def test_clean_name_drops_search_stuffing():
    assert clean_name("A N Bhutada & CO Best CA firm in Pune | Top Gst consultant | CA") == "A N Bhutada & CO Best CA firm in Pune"


def test_distinctive_tokens_drop_generic_words_and_initials():
    assert distinctive_tokens("A N Bhutada & CO Best CA firm in Pune | Top Gst consultant") == ["bhutada", "pune"]
    assert distinctive_tokens("Sharma Tax Consultants Pvt Ltd") == ["sharma"]
    assert distinctive_tokens("CA & Co Chartered Accountants") == []


def test_guess_domains_use_distinctive_words_and_common_tlds():
    guesses = guess_domains("Kumar Patel Associates")
    assert guesses[:3] == ["kumarpatel.com", "kumarpatel.in", "kumarpatel.co.in"]


def test_guess_domains_skip_names_that_are_too_short_to_guess():
    assert guess_domains("Jain & Co") == []
    assert guess_domains("CA & Co") == []


def test_directory_domains_are_recognised_including_subdomains():
    assert is_directory_domain("www.justdial.com")
    assert is_directory_domain("justdial.com")
    assert is_directory_domain("m.facebook.com")
    assert not is_directory_domain("kumarpatel.com")


def test_page_must_mention_name_city_and_finance():
    assert page_matches("Kumar Patel Associates", "Pune", firm_page("Kumar Patel Associates", "Pune"))
    assert not page_matches("Kumar Patel Associates", "Pune", firm_page("Kumar Patel Associates", "Chennai"))
    assert not page_matches("Kumar Patel Associates", "Pune", firm_page("Someone Else", "Pune"))
    assert not page_matches(
        "Kumar Patel Associates", "Pune", firm_page("Kumar Patel", "Pune", extra="We sell garden furniture.")
    )
    assert not page_matches("CA & Co", "Pune", firm_page("CA & Co", "Pune"))


def tavily_transport(results, status=200):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json={"results": [{"url": url} for url in results]})

    transport = httpx.MockTransport(handler)
    transport.seen = seen
    return transport


async def test_tavily_sends_the_key_in_a_header_and_returns_urls():
    transport = tavily_transport(["https://a.example/", "https://b.example/"])
    urls = await tavily.search("secret-key", "Kumar Patel Pune", transport=transport)

    assert urls == ["https://a.example/", "https://b.example/"]
    request = transport.seen[0]
    assert request.headers["authorization"] == "Bearer secret-key"
    assert "secret-key" not in str(request.url)
    assert json.loads(request.content)["query"] == "Kumar Patel Pune"


async def test_tavily_quota_and_error_responses_raise_without_leaking_the_key():
    with pytest.raises(tavily.QuotaExhausted):
        await tavily.search("secret-key", "q", transport=tavily_transport([], status=432))
    with pytest.raises(tavily.TavilyError) as error:
        await tavily.search("secret-key", "q", transport=tavily_transport([], status=500))
    assert "secret-key" not in str(error.value)
    with pytest.raises(tavily.TavilyError):
        await tavily.search("", "q")


def site_transport(sites):
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        pages = sites.get(request.url.host)
        if pages is None:
            raise httpx.ConnectError("no such host")
        body = pages.get(request.url.path)
        if body is None:
            return httpx.Response(404, text="not found", headers={"content-type": "text/plain"})
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    transport.requested = requested
    return transport


def client_for(sites):
    async def no_sleep(_):
        return None

    transport = site_transport(sites)
    return PoliteClient(fast_settings(), transport=transport, sleep=no_sleep), transport


async def add_listing(engine, name, city, verification="unverified", email=None, website=None, number=None):
    async with AsyncSession(engine) as session:
        source = await session.scalar(select(DataSource).where(DataSource.key == f"finder_{verification}"))
        if source is None:
            source = DataSource(
                key=f"finder_{verification}", name=verification, regulator="TEST",
                default_profession_type="investment_adviser", base_url="https://x.test", is_enabled=True,
                verification_level=verification,
            )
            session.add(source)
            await session.flush()
        professional = FinancialProfessional(display_name=name, name_normalized=name.lower(), kind="firm")
        session.add(professional)
        await session.flush()
        session.add(
            ProfessionalRegistration(
                professional_id=professional.id, source_id=source.id, profession_type="investment_adviser",
                registration_number=number or f"R-{name}", status="active", city=city, email=email,
                attributes={"website": website} if website else {},
                source_url="https://x.test", content_hash="h", missing_runs=0,
            )
        )
        professional_id = professional.id
        await session.commit()
        return professional_id


async def lookup_for(engine, professional_id):
    async with AsyncSession(engine) as session:
        return await session.scalar(select(WebsiteLookup).where(WebsiteLookup.professional_id == professional_id))


async def websites_for(engine, professional_id):
    async with AsyncSession(engine) as session:
        return (
            await session.scalars(select(ProfessionalWebsite).where(ProfessionalWebsite.professional_id == professional_id))
        ).all()


async def yes(_domain):
    return True


async def no(_domain):
    return False


def settings(**overrides):
    return ScrapeSettings(
        scrape_min_interval_seconds=0.0, scrape_max_retries=1, tavily_api_key="key", **overrides
    )


async def test_a_listing_matching_a_register_entry_borrows_its_known_domain(engine, tmp_path):
    await add_listing(engine, "Kumar Patel Associates", "Pune", verification="verified", email="info@kumarpatelca.com")
    listing = await add_listing(engine, "Kumar Patel & Co Chartered Accountants", "Pune")
    client, transport = client_for({})

    async with client:
        summary = await find_websites(
            client=client, settings=settings(), ledger_path=tmp_path / "t.json", search=False, resolver=no, now=NOW
        )

    assert summary.found_by_register == 1
    lookup = await lookup_for(engine, listing)
    assert (lookup.status, lookup.method, lookup.domain) == ("found", "register_match", "kumarpatelca.com")
    site = (await websites_for(engine, listing))[0]
    assert (site.domain, site.derived_from, site.check_status) == ("kumarpatelca.com", "register_match", "pending")
    assert transport.requested == []


async def test_register_match_needs_the_same_city(engine, tmp_path):
    await add_listing(engine, "Kumar Patel Associates", "Mumbai", verification="verified", email="info@kumarpatelca.com")
    listing = await add_listing(engine, "Kumar Patel & Co", "Pune")
    client, _ = client_for({})

    async with client:
        await find_websites(
            client=client, settings=settings(), ledger_path=tmp_path / "t.json", search=False, resolver=no, now=NOW
        )

    assert (await lookup_for(engine, listing)).status == "needs_search"
    assert await websites_for(engine, listing) == []


async def test_a_guessed_domain_is_accepted_only_when_the_homepage_matches(engine, tmp_path):
    good = await add_listing(engine, "Kumar Patel Associates", "Pune")
    wrong = await add_listing(engine, "Rao Mehra Associates", "Pune")
    sites = {
        "kumarpatel.com": {"/": firm_page("Kumar Patel Associates", "Pune")},
        "raomehra.com": {"/": firm_page("Unrelated Shop", "Delhi", extra="We sell furniture.")},
    }
    client, _ = client_for(sites)

    async with client:
        summary = await find_websites(
            client=client, settings=settings(), ledger_path=tmp_path / "t.json", search=False, resolver=yes, now=NOW
        )

    assert summary.found_by_guess == 1
    assert (await lookup_for(engine, good)).method == "domain_guess"
    assert (await websites_for(engine, good))[0].derived_from == "domain_guess"
    assert (await lookup_for(engine, wrong)).status == "needs_search"
    assert await websites_for(engine, wrong) == []


async def test_guess_skips_domains_that_do_not_resolve(engine, tmp_path):
    await add_listing(engine, "Kumar Patel Associates", "Pune")
    client, transport = client_for({"kumarpatel.com": {"/": firm_page("Kumar Patel Associates", "Pune")}})

    async with client:
        await find_websites(
            client=client, settings=settings(), ledger_path=tmp_path / "t.json", search=False, resolver=no, now=NOW
        )

    assert transport.requested == []


async def test_search_finds_a_site_skips_directories_and_verifies_the_page(engine, tmp_path):
    listing = await add_listing(engine, "Zed Quartz Advisers", "Pune")
    sites = {
        "zedquartz.net": {"/": firm_page("Zed Quartz Advisers", "Pune")},
        "justdial.com": {"/": firm_page("Zed Quartz Advisers", "Pune")},
    }
    client, transport = client_for(sites)
    search = tavily_transport(["https://www.justdial.com/zed", "https://zedquartz.net/about"])

    async with client:
        summary = await find_websites(
            client=client, settings=settings(), ledger_path=tmp_path / "t.json", resolver=no,
            tavily_transport=search, now=NOW,
        )

    assert summary.found_by_search == 1
    assert summary.searches_made == 1
    assert (await lookup_for(engine, listing)).domain == "zedquartz.net"
    assert not any("justdial" in url for url in transport.requested)


async def test_a_search_result_that_does_not_match_is_recorded_as_not_found(engine, tmp_path):
    listing = await add_listing(engine, "Zed Quartz Advisers", "Pune")
    client, _ = client_for({"other.example.org": {"/": firm_page("Other Firm", "Delhi")}})
    search = tavily_transport(["https://other.example.org/"])

    async with client:
        await find_websites(
            client=client, settings=settings(), ledger_path=tmp_path / "t.json", resolver=no,
            tavily_transport=search, now=NOW,
        )

    assert (await lookup_for(engine, listing)).status == "not_found"
    assert await websites_for(engine, listing) == []


async def test_search_stops_at_the_daily_limit_and_resumes_next_day(engine, tmp_path):
    for name in ("Alpha Quartz Advisers", "Beta Quartz Advisers", "Gamma Quartz Advisers"):
        await add_listing(engine, name, "Pune")
    client, _ = client_for({})
    search = tavily_transport([])
    ledger = tmp_path / "t.json"

    async with client:
        first = await find_websites(
            client=client, settings=settings(website_search_daily_limit=2), ledger_path=ledger, resolver=no,
            tavily_transport=search, now=NOW,
        )
        assert first.searches_made == 2
        assert first.left_for_search == 1
        assert "limit" in first.stopped_reason
        assert len(search.seen) == 2

        again = await find_websites(
            client=client, settings=settings(website_search_daily_limit=2), ledger_path=ledger, resolver=no,
            tavily_transport=search, now=NOW,
        )
        assert again.searches_made == 0

        next_day = await find_websites(
            client=client, settings=settings(website_search_daily_limit=2), ledger_path=ledger, resolver=no,
            tavily_transport=search, now=datetime(2026, 11, 5, 12, tzinfo=timezone.utc),
        )
        assert next_day.searches_made == 1
        assert next_day.left_for_search == 0


async def test_without_a_tavily_key_the_free_steps_still_run(engine, tmp_path):
    listing = await add_listing(engine, "Zed Quartz Advisers", "Pune")
    client, _ = client_for({})

    async with client:
        summary = await find_websites(
            client=client,
            settings=ScrapeSettings(scrape_min_interval_seconds=0.0, scrape_max_retries=1, tavily_api_key=""),
            ledger_path=tmp_path / "t.json", resolver=no, now=NOW,
        )

    assert summary.searches_made == 0
    assert "TAVILY_API_KEY" in summary.stopped_reason
    assert (await lookup_for(engine, listing)).status == "needs_search"


async def test_quota_error_from_tavily_stops_the_run_without_marking_rows(engine, tmp_path):
    listing = await add_listing(engine, "Zed Quartz Advisers", "Pune")
    client, _ = client_for({})

    async with client:
        summary = await find_websites(
            client=client, settings=settings(), ledger_path=tmp_path / "t.json", resolver=no,
            tavily_transport=tavily_transport([], status=429), now=NOW,
        )

    assert "quota" in summary.stopped_reason.lower()
    assert (await lookup_for(engine, listing)).status == "needs_search"


async def test_listings_that_already_have_a_website_or_are_register_rows_are_left_alone(engine, tmp_path):
    with_site = await add_listing(engine, "Kumar Patel Associates", "Pune", website="https://own.example.com")
    register_row = await add_listing(engine, "Zed Quartz Advisers", "Pune", verification="verified")
    client, _ = client_for({})

    async with client:
        summary = await find_websites(
            client=client, settings=settings(), ledger_path=tmp_path / "t.json", resolver=no,
            tavily_transport=tavily_transport([]), now=NOW,
        )

    assert summary.rows_considered == 0
    assert await lookup_for(engine, with_site) is None
    assert await lookup_for(engine, register_row) is None


async def test_rerun_does_not_repeat_finished_lookups(engine, tmp_path):
    await add_listing(engine, "Zed Quartz Advisers", "Pune")
    client, _ = client_for({})
    search = tavily_transport([])
    ledger = tmp_path / "t.json"

    async with client:
        await find_websites(client=client, settings=settings(), ledger_path=ledger, resolver=no, tavily_transport=search, now=NOW)
        second = await find_websites(client=client, settings=settings(), ledger_path=ledger, resolver=no, tavily_transport=search, now=NOW)

    assert second.rows_considered == 0
    assert second.searches_made == 0
    assert len(search.seen) == 1
