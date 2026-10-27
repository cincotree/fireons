from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import (
    DataSource,
    FinancialProfessional,
    NriSignal,
    ProfessionalRegistration,
    ProfessionalWebsite,
)
from enrichment.__main__ import _review, _review_queue
from enrichment.crawler import check_site
from enrichment.runner import enrich_nri
from scraping.http import PoliteClient
from tests.scraping_helpers import fast_settings

NRI_HOME = """<html><head><title>Sample Advisers</title></head><body>
<nav><a href="/nri-services">NRI Services</a><a href="/contact">Contact</a><a href="https://other.example.org/nri">Partner</a></nav>
<p>Mutual funds and planning.</p></body></html>"""
NRI_PAGE = "<html><body><h1>Investing from abroad as an NRI</h1><p>NRE and NRO accounts supported.</p></body></html>"
PLAIN_HOME = "<html><body><p>Mutual funds and insurance only.</p></body></html>"

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


def site_transport(sites: dict[str, dict[str, tuple[int, str, str]]]):
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        requested.append(str(request.url))
        pages = sites.get(host)
        if pages is None:
            raise httpx.ConnectError("no such host")
        status, content_type, body = pages.get(request.url.path, (404, "text/plain", "not found"))
        return httpx.Response(status, text=body, headers={"content-type": content_type})

    transport = httpx.MockTransport(handler)
    transport.requested = requested
    return transport


def html(body):
    return (200, "text/html; charset=utf-8", body)


def client_for(sites):
    async def no_sleep(_: float) -> None:
        return None

    transport = site_transport(sites)
    return PoliteClient(fast_settings(), transport=transport, sleep=no_sleep), transport


async def add_professional(engine, name, email, status="active"):
    async with AsyncSession(engine) as session:
        source = await session.scalar(select(DataSource).where(DataSource.key == "enrich_test"))
        if source is None:
            source = DataSource(
                key="enrich_test", name="Test", regulator="TEST",
                default_profession_type="investment_adviser", base_url="https://x.test", is_enabled=True,
            )
            session.add(source)
            await session.flush()
        professional = FinancialProfessional(display_name=name, name_normalized=name.lower(), kind="firm")
        session.add(professional)
        await session.flush()
        session.add(
            ProfessionalRegistration(
                professional_id=professional.id, source_id=source.id, profession_type="investment_adviser",
                registration_number=f"T-{name}", status=status, email=email, attributes={},
                source_url="https://x.test", content_hash="h", missing_runs=0,
            )
        )
        professional_id = professional.id
        await session.commit()
        return professional_id


async def signals_for(engine, professional_id):
    async with AsyncSession(engine) as session:
        return (await session.scalars(select(NriSignal).where(NriSignal.professional_id == professional_id))).all()


async def website_for(engine, professional_id):
    async with AsyncSession(engine) as session:
        return await session.scalar(
            select(ProfessionalWebsite).where(ProfessionalWebsite.professional_id == professional_id)
        )


NRI_SITE = {
    "nrifirm.com": {
        "/robots.txt": (200, "text/plain", "User-agent: *\nDisallow: /private/"),
        "/": html(NRI_HOME),
        "/nri-services": html(NRI_PAGE),
        "/contact": html(PLAIN_HOME),
    }
}


async def test_crawler_follows_nri_links_on_the_same_site_only():
    client, transport = client_for(NRI_SITE)
    async with client:
        result = await check_site("nrifirm.com", client, fast_settings())

    assert result.status == "checked"
    assert result.pages_checked == 2
    assert any(s.page_url.endswith("/nri-services") for s in result.signals)
    assert not any("other.example.org" in url for url in transport.requested)


async def test_navigation_repeated_on_every_page_is_reported_once():
    nav = '<nav><a href="/nri-services">NRI Investment Advisory</a></nav>'
    sites = {
        "navfirm.com": {
            "/": html(f"<html><body>{nav}<p>Home</p></body></html>"),
            "/nri-services": html(f"<html><body>{nav}<p>Services</p></body></html>"),
        }
    }
    client, _ = client_for(sites)
    async with client:
        result = await check_site("navfirm.com", client, fast_settings())

    assert result.pages_checked == 2
    assert [s.matched_text for s in result.signals] == ["NRI Investment Advisory"]


async def test_crawler_respects_robots_disallow_for_the_whole_site():
    sites = {"closed.com": {"/robots.txt": (200, "text/plain", "User-agent: *\nDisallow: /"), "/": html(NRI_HOME)}}
    client, transport = client_for(sites)
    async with client:
        result = await check_site("closed.com", client, fast_settings())

    assert result.status == "blocked_by_robots"
    assert result.signals == []
    assert not any(url.endswith("closed.com/") for url in transport.requested)


async def test_crawler_skips_individual_pages_disallowed_by_robots():
    sites = {"nrifirm.com": {**NRI_SITE["nrifirm.com"], "/robots.txt": (200, "text/plain", "User-agent: *\nDisallow: /nri-services")}}
    client, _ = client_for(sites)
    async with client:
        result = await check_site("nrifirm.com", client, fast_settings())

    assert not any(s.page_url.endswith("/nri-services") for s in result.signals)


async def test_unreachable_site_is_reported_not_raised():
    client, _ = client_for({})
    async with client:
        result = await check_site("gone.com", client, fast_settings())

    assert result.status == "unreachable"
    assert result.error


async def test_non_html_homepage_is_unreachable():
    sites = {"pdfonly.com": {"/": (200, "application/pdf", "%PDF")}}
    client, _ = client_for(sites)
    async with client:
        result = await check_site("pdfonly.com", client, fast_settings())

    assert result.status == "unreachable"


async def test_run_stores_signals_with_text_confidence_and_pending_review(engine):
    pid = await add_professional(engine, "Nri Firm", "desk@nrifirm.com")
    client, _ = client_for(NRI_SITE)
    async with client:
        summary = await enrich_nri(client=client, settings=fast_settings(), now=NOW)

    assert (summary.websites_checked, summary.unreachable) == (1, 0)
    signals = await signals_for(engine, pid)
    assert summary.signals_found == len(signals) > 0
    assert {s.review_status for s in signals} == {"pending"}
    assert any(s.confidence == "high" and "NRI" in s.matched_text for s in signals)
    site = await website_for(engine, pid)
    assert (site.check_status, site.pages_checked, site.derived_from) == ("checked", 2, "email_domain")
    assert site.last_checked_at == NOW


async def test_site_without_signals_is_marked_checked_with_no_tags(engine):
    pid = await add_professional(engine, "Plain Firm", "hi@plainfirm.com")
    client, _ = client_for({"plainfirm.com": {"/": html(PLAIN_HOME)}})
    async with client:
        await enrich_nri(client=client, settings=fast_settings(), now=NOW)

    assert await signals_for(engine, pid) == []
    assert (await website_for(engine, pid)).check_status == "checked"


async def test_generic_and_missing_emails_and_delisted_registrations_are_not_crawled(engine):
    await add_professional(engine, "Gmail Person", "someone@gmail.com")
    await add_professional(engine, "No Email", None)
    await add_professional(engine, "Delisted Firm", "a@delistedfirm.com", status="delisted")
    client, transport = client_for(NRI_SITE)
    async with client:
        summary = await enrich_nri(client=client, settings=fast_settings(), now=NOW)

    assert summary.websites_known == 0
    assert transport.requested == []


async def test_recent_checks_are_skipped_and_old_ones_repeated(engine):
    await add_professional(engine, "Nri Firm", "desk@nrifirm.com")
    client, transport = client_for(NRI_SITE)
    async with client:
        await enrich_nri(client=client, settings=fast_settings(), now=NOW)
        first = len(transport.requested)
        again = await enrich_nri(client=client, settings=fast_settings(), now=NOW + timedelta(days=5))
        assert again.websites_checked == 0
        assert len(transport.requested) == first
        later = await enrich_nri(client=client, settings=fast_settings(), now=NOW + timedelta(days=40))
    assert later.websites_checked == 1


async def test_rerun_keeps_reviews_and_drops_stale_pending_signals(engine):
    pid = await add_professional(engine, "Nri Firm", "desk@nrifirm.com")
    client, _ = client_for(NRI_SITE)
    async with client:
        await enrich_nri(client=client, settings=fast_settings(), now=NOW)
    signals = await signals_for(engine, pid)
    confirmed_id = signals[0].id
    async with AsyncSession(engine) as session:
        (await session.get(NriSignal, confirmed_id)).review_status = "confirmed"
        await session.commit()

    plain, _ = client_for({"nrifirm.com": {"/": html(PLAIN_HOME)}})
    async with plain:
        summary = await enrich_nri(client=plain, settings=fast_settings(), now=NOW + timedelta(days=40))

    remaining = await signals_for(engine, pid)
    assert summary.signals_removed == len(signals) - 1
    assert [s.id for s in remaining] == [confirmed_id]
    assert remaining[0].review_status == "confirmed"


async def test_unreachable_site_keeps_existing_signals(engine):
    pid = await add_professional(engine, "Nri Firm", "desk@nrifirm.com")
    client, _ = client_for(NRI_SITE)
    async with client:
        await enrich_nri(client=client, settings=fast_settings(), now=NOW)
    before = len(await signals_for(engine, pid))

    down, _ = client_for({})
    async with down:
        summary = await enrich_nri(client=down, settings=fast_settings(), now=NOW + timedelta(days=40))

    assert summary.unreachable == 1
    assert len(await signals_for(engine, pid)) == before
    assert (await website_for(engine, pid)).check_status == "unreachable"


async def test_identical_rerun_does_not_duplicate_signals(engine):
    pid = await add_professional(engine, "Nri Firm", "desk@nrifirm.com")
    client, _ = client_for(NRI_SITE)
    async with client:
        await enrich_nri(client=client, settings=fast_settings(), now=NOW)
        count = len(await signals_for(engine, pid))
        await enrich_nri(client=client, settings=fast_settings(), now=NOW + timedelta(days=40))

    assert len(await signals_for(engine, pid)) == count


async def test_limit_caps_the_websites_checked_per_run(engine):
    await add_professional(engine, "Firm A", "a@firma.com")
    await add_professional(engine, "Firm B", "b@firmb.com")
    sites = {"firma.com": {"/": html(PLAIN_HOME)}, "firmb.com": {"/": html(PLAIN_HOME)}}
    client, _ = client_for(sites)
    async with client:
        summary = await enrich_nri(client=client, settings=fast_settings(), limit=1, now=NOW)

    assert summary.websites_checked == 1


async def test_review_cli_updates_status_and_rejects_unknown_ids(engine, capsys):
    pid = await add_professional(engine, "Nri Firm", "desk@nrifirm.com")
    client, _ = client_for(NRI_SITE)
    async with client:
        await enrich_nri(client=client, settings=fast_settings(), now=NOW)
    signal = (await signals_for(engine, pid))[0]

    assert await _review_queue("high", 10) == 0
    assert signal.id in capsys.readouterr().out
    assert await _review(signal.id, "rejected") == 0
    assert await _review("00000000-0000-0000-0000-000000000000", "confirmed") == 1
    async with AsyncSession(engine) as session:
        stored = await session.get(NriSignal, signal.id)
    assert (stored.review_status, stored.reviewed_at is not None) == ("rejected", True)
