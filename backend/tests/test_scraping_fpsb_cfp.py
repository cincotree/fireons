import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import ProfessionalRegistration
from scraping.http import PoliteClient
from scraping.runner import run_source
from scraping.sources.fpsb_cfp import FpsbCfpSource, parse_listing_page
from scraping.types import ProfessionalKind, ProfessionType, RunStatus, ScrapeHttpError
from tests.scraping_helpers import fast_settings

ROWS = [
    ("1", "IN900001", "ASHA FICTIONAL", "Testville"),
    ("2", "IN900002", "Ravi Imaginary", "BAngalore "),
    ("3", "IN900003", "Meera Placeholder", ""),
]


def render(rows=ROWS, header=True):
    head = "<tr><th>Sl No</th><th>FPSB Number</th><th>Name</th><th>City</th><th>Contact CFP</th></tr>" if header else ""
    body = "".join(
        f"<tr><td>{a}</td><td>{b}</td><!-- <td></td> --><td>{c}</td><td>{d}</td>"
        '<td><a href="https://example.test/?user_id=1">Enquiry</a></td></tr>'
        for a, b, c, d in rows
    )
    return f"<html><body><table>{head}{body}</table></body></html>"


def client_for(html: str, status: int = 200) -> PoliteClient:
    async def no_sleep(_: float) -> None:
        return None

    transport = httpx.MockTransport(lambda request: httpx.Response(status, text=html))
    return PoliteClient(fast_settings(), transport=transport, sleep=no_sleep)


@pytest_asyncio.fixture
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


async def scrape(html: str, status: int = 200):
    async with client_for(html, status) as client:
        return await run_source("fpsb_cfp", client=client, settings=fast_settings())


def test_rows_are_parsed_with_the_serial_number_as_the_expected_total():
    page = parse_listing_page(render())

    assert [r.registration_number for r in page.records] == ["IN900001", "IN900002", "IN900003"]
    assert page.expected_total == 3
    assert page.parse_errors == 0


def test_fields_are_normalized_and_no_contact_details_are_kept():
    first, second, third = parse_listing_page(render()).records

    assert first.name == "Asha Fictional"
    assert first.kind == ProfessionalKind.INDIVIDUAL
    assert first.profession_type == ProfessionType.CERTIFIED_FINANCIAL_PLANNER
    assert (first.city, second.city, third.city) == ("Testville", "Bangalore", None)
    assert second.name == "Ravi Imaginary"
    assert first.email is None and first.phone is None and first.address_raw is None
    assert first.attributes == {"certification": "CFP"}


@pytest.mark.parametrize(
    "bad_row",
    [("4", "BADNUMBER", "Bad Number", "Pune"), ("4", "IN900004", "  ", "Pune"), ("4", "IN9", "Short", "Pune")],
)
def test_invalid_rows_count_as_parse_errors(bad_row):
    page = parse_listing_page(render([*ROWS, bad_row]))

    assert page.parse_errors == 1
    assert len(page.records) == 3
    assert page.expected_total == 4


def test_page_without_a_table_is_empty():
    assert parse_listing_page("<html><body>maintenance</body></html>").records == []


async def test_missing_table_is_an_error_not_an_empty_success():
    async with client_for("<html><body>maintenance</body></html>") as client:
        with pytest.raises(ScrapeHttpError, match="layout"):
            [page async for page in FpsbCfpSource().fetch_pages(client)]


@pytest.mark.usefixtures("use_test_engine")
async def test_full_run_stores_everyone_and_a_rerun_changes_nothing(engine):
    first = await scrape(render())
    second = await scrape(render())

    assert first.status == RunStatus.SUCCEEDED
    assert (first.records_seen, first.inserted, first.expected_total) == (3, 3, 3)
    assert (second.inserted, second.updated, second.unchanged) == (0, 0, 3)
    async with AsyncSession(engine) as session:
        rows = (await session.scalars(select(ProfessionalRegistration))).all()
    assert {r.profession_type for r in rows} == {"certified_financial_planner"}


@pytest.mark.usefixtures("use_test_engine")
async def test_capitalisation_differences_in_city_do_not_count_as_changes():
    await scrape(render())
    fixed = [ROWS[0], ("2", "IN900002", "Ravi Imaginary", "Bangalore"), ROWS[2]]

    summary = await scrape(render(fixed))

    assert (summary.updated, summary.unchanged) == (0, 3)


@pytest.mark.usefixtures("use_test_engine")
async def test_site_outage_fails_the_run_and_a_bad_row_makes_it_partial(engine):
    down = await scrape(render(), status=503)
    partial = await scrape(render([*ROWS, ("4", "BAD", "Bad", "Pune")]))

    assert down.status == RunStatus.FAILED
    assert partial.status == RunStatus.PARTIAL
