from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import ProfessionalRegistration, ScrapeRun
from scraping.runner import run_source
from scraping.sources.amfi_arn import (
    AmfiArnSource,
    parse_api_page,
    parse_city_list,
    state_from_pincode,
    to_registration,
)
from scraping.types import (
    ParseError,
    ProfessionalKind,
    ProfessionType,
    RunStatus,
    ScrapeHttpError,
)
from tests.fixtures.generate_amfi_fixtures import (
    ALL_GOOD_ROWS,
    BROKEN_ROW,
    CITIES,
    ROWS_BY_CITY,
    SAMPLEPUR_ROWS,
    TESTVILLE_ROWS,
    render_api_page,
    render_locate_page,
)
from tests.scraping_helpers import amfi_client, fast_settings


@pytest_asyncio.fixture
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


async def collect(client):
    return [page async for page in AmfiArnSource().fetch_pages(client)]


async def scrape(rows_by_city=ROWS_BY_CITY, cities=CITIES, **client_kwargs):
    async with amfi_client(rows_by_city, cities, **client_kwargs) as client:
        return await run_source("amfi_arn", client=client, settings=fast_settings())


def test_city_list_is_read_from_the_page_and_deduplicated_ignoring_case():
    cities = parse_city_list(render_locate_page(CITIES))

    assert cities == ["Testville", "Samplepur", "Emptytown"]


def test_city_list_handles_names_with_commas_and_punctuation():
    cities = parse_city_list(render_locate_page(["Zirakpur,Sahibzada Ajit Singh Nagar", "St. John's"]))

    assert cities == ["Zirakpur,Sahibzada Ajit Singh Nagar", "St. John's"]


def test_page_without_city_list_gives_empty_result():
    assert parse_city_list("<html><body>nothing</body></html>") == []


def test_full_record_fields_are_normalized():
    record = to_registration(TESTVILLE_ROWS[0])

    assert record.registration_number == "ARN-100001"
    assert record.name == "Example Distributors Private Limited"
    assert record.kind == ProfessionalKind.FIRM
    assert record.profession_type == ProfessionType.MF_DISTRIBUTOR
    assert record.valid_from == date(2023, 4, 1)
    assert record.valid_until == date(2028, 3, 31)
    assert record.city == "Testville"
    assert record.state == "Maharashtra"
    assert record.pincode == "400001"
    assert record.email == "desk@example.com"
    assert record.phone == "9100000001"
    assert record.contact_person is None
    assert record.source_url == "https://www.amfiindia.com/locate-distributor"
    assert record.attributes == {
        "euin": "E000001",
        "kyd_compliant": "Y",
        "residence_phone": "9100000002",
        "state_inferred_from_pincode": True,
    }


def test_missing_optional_fields_become_none_and_empty_attributes_are_dropped():
    record = to_registration(TESTVILLE_ROWS[1])

    assert record.registration_number == "ARN-42"
    assert record.kind == ProfessionalKind.INDIVIDUAL
    assert record.email is None
    assert record.phone == "9100000003"
    assert record.attributes == {
        "kyd_compliant": "N",
        "sif_valid_from": "2025-01-01T00:00:00.000Z",
        "sif_valid_till": "2028-01-01T00:00:00.000Z",
        "state_inferred_from_pincode": True,
    }


def test_record_without_expiry_has_no_valid_until_and_invalid_pin_is_dropped():
    record = to_registration(TESTVILLE_ROWS[2])

    assert record.valid_until is None
    assert record.pincode is None
    assert record.state is None
    assert record.phone == "9100000004"
    assert "residence_phone" not in record.attributes


def test_state_is_inferred_from_pincode_when_the_address_has_none():
    record = to_registration(SAMPLEPUR_ROWS[0])

    assert record.state == "Kerala"
    assert record.attributes["state_inferred_from_pincode"] is True


@pytest.mark.parametrize(
    "pincode,state",
    [
        ("110001", "Delhi"),
        ("403001", "Goa"),
        ("400001", "Maharashtra"),
        ("682001", "Kerala"),
        ("682551", "Lakshadweep"),
        ("605001", None),
        ("000000", None),
        ("12345", None),
        (None, None),
    ],
)
def test_pincode_prefix_lookup(pincode, state):
    assert state_from_pincode(pincode) == state


@pytest.mark.parametrize(
    "overrides",
    [
        {"ARN": "ABC"},
        {"ARN": ""},
        {"ARN": None},
        {"ARNHolderName": "  "},
        {"ARNValidFrom": "sometime in 2020"},
        {"ARNValidTill": "2000-01-01T00:00:00.000Z"},
    ],
)
def test_invalid_rows_raise_parse_error(overrides):
    with pytest.raises(ParseError):
        to_registration({**TESTVILLE_ROWS[0], **overrides})


def test_api_page_counts_unparseable_rows_instead_of_crashing():
    payload = render_api_page({"samplepur": SAMPLEPUR_ROWS + [BROKEN_ROW]}, "Samplepur", 1, 50)

    page, total, page_count = parse_api_page(payload)

    assert (total, page_count) == (3, 1)
    assert page.parse_errors == 1
    assert [r.registration_number for r in page.records] == ["ARN-100004", "ARN-100005"]


@pytest.mark.parametrize("payload", [{"success": False, "message": "no filter"}, [], {"data": None}])
def test_unexpected_api_payload_is_an_error(payload):
    with pytest.raises(ScrapeHttpError):
        parse_api_page(payload)


async def test_source_walks_every_city_and_page_with_running_expected_total():
    async with amfi_client(ROWS_BY_CITY, CITIES, page_size=2) as client:
        pages = await collect(client)

    numbers = [r.registration_number for p in pages for r in p.records]
    assert numbers == ["ARN-100001", "ARN-42", "ARN-100003", "ARN-100004", "ARN-100005"]
    assert [p.expected_total for p in pages] == [3, 3, 5]


async def test_source_skips_cities_with_no_distributors():
    async with amfi_client(ROWS_BY_CITY, ["Emptytown"]) as client:
        pages = await collect(client)

    assert pages == []


async def test_source_fails_when_the_city_list_is_missing():
    async with amfi_client(ROWS_BY_CITY, []) as client:
        with pytest.raises(ScrapeHttpError, match="city list"):
            await collect(client)


async def test_source_surfaces_http_failures():
    async with amfi_client(ROWS_BY_CITY, CITIES, api_status=503) as client:
        with pytest.raises(ScrapeHttpError):
            await collect(client)


@pytest.mark.usefixtures("use_test_engine")
async def test_full_run_stores_every_distributor(engine):
    summary = await scrape()

    assert summary.status == RunStatus.SUCCEEDED
    assert (summary.records_seen, summary.inserted, summary.expected_total) == (5, 5, 5)
    async with AsyncSession(engine) as session:
        rows = (await session.scalars(select(ProfessionalRegistration))).all()
        run_row = await session.scalar(select(ScrapeRun))
    assert {r.registration_number for r in rows} == {f"ARN-{r['ARN']}" for r in ALL_GOOD_ROWS}
    assert {r.profession_type for r in rows} == {"mf_distributor"}
    assert run_row.status == "succeeded"


@pytest.mark.usefixtures("use_test_engine")
async def test_rerun_with_unchanged_data_writes_nothing():
    await scrape()

    summary = await scrape()

    assert (summary.inserted, summary.updated, summary.unchanged) == (0, 0, 5)


@pytest.mark.usefixtures("use_test_engine")
async def test_changed_row_is_updated_not_duplicated():
    await scrape()
    changed = {**ROWS_BY_CITY, "samplepur": [{**SAMPLEPUR_ROWS[0], "Email": "new@example.com"}, SAMPLEPUR_ROWS[1]]}

    summary = await scrape(changed)

    assert (summary.inserted, summary.updated, summary.unchanged) == (0, 1, 4)


@pytest.mark.usefixtures("use_test_engine")
async def test_unparseable_row_makes_the_run_partial_without_losing_the_rest():
    rows = {**ROWS_BY_CITY, "samplepur": SAMPLEPUR_ROWS + [BROKEN_ROW]}

    summary = await scrape(rows)

    assert summary.status == RunStatus.PARTIAL
    assert summary.parse_errors == 1
    assert summary.inserted == 5


@pytest.mark.usefixtures("use_test_engine")
async def test_register_site_outage_fails_the_run_and_stores_nothing(engine):
    summary = await scrape(api_status=503)

    assert summary.status == RunStatus.FAILED
    assert summary.error
    async with AsyncSession(engine) as session:
        assert (await session.scalars(select(ProfessionalRegistration))).all() == []


@pytest.mark.usefixtures("use_test_engine")
async def test_distributor_missing_from_a_successful_run_is_flagged_only_after_two_runs(engine):
    await scrape()
    shrunk = {**ROWS_BY_CITY, "samplepur": [SAMPLEPUR_ROWS[0]]}

    await scrape(shrunk)
    async with AsyncSession(engine) as session:
        first = await session.scalar(
            select(ProfessionalRegistration).where(ProfessionalRegistration.registration_number == "ARN-100005")
        )
    await scrape(shrunk)
    async with AsyncSession(engine) as session:
        second = await session.scalar(
            select(ProfessionalRegistration).where(ProfessionalRegistration.registration_number == "ARN-100005")
        )

    assert first.status != "delisted"
    assert second.status == "delisted"
