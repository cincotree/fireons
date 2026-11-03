import csv
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import database.session as database_session
from database.models import DataSource, ProfessionalRegistration
from enrichment.places import CSV_COLUMNS
from scraping.runner import run_source
from scraping.sources import SOURCES
from scraping.sources.google_places import (
    DEFINITION,
    GooglePlacesCsvSource,
    parse_google_address,
    read_csv,
    rejection_reason,
    to_registration,
)
from scraping.types import ParseError, ProfessionalKind, ProfessionType, RunStatus
from tests.scraping_helpers import fast_settings


def row(number: int, **overrides) -> dict:
    values = {
        "place_id": f"place-{number}",
        "name": f"Sample Advisers {number}",
        "category": "chartered_accountant",
        "searched_city": "Testville",
        "address": f"{number} Test Road, Testville, Maharashtra 411001, India",
        "latitude": "12.5",
        "longitude": "77.5",
        "phone": "099999 00000",
        "website": f"https://firm{number}.example.com/",
        "google_maps_url": f"https://maps.example.test/{number}",
        "business_status": "OPERATIONAL",
        "types": "accounting;point_of_interest",
        "fetched_at": "2026-11-03T10:00:00",
    }
    values.update(overrides)
    return values


def write_csv(path: Path, rows: list[dict]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest_asyncio.fixture
async def use_test_engine(engine, monkeypatch):
    monkeypatch.setattr(database_session, "_engine", engine)
    monkeypatch.setattr(
        database_session,
        "_async_session_factory",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )


async def load(path: Path):
    return await run_source(
        "google_places", source=GooglePlacesCsvSource(path), settings=fast_settings()
    )


def test_the_import_source_is_unverified_and_never_scheduled():
    assert DEFINITION.verification_level == "unverified"
    assert DEFINITION.regulator == "Google Maps"
    assert "google_places" not in SOURCES
    assert GooglePlacesCsvSource.allows_delisting is False


def test_row_is_mapped_to_a_registration():
    record = to_registration(row(1))

    assert record.registration_number == "GP-place-1"
    assert record.name == "Sample Advisers 1"
    assert record.kind == ProfessionalKind.FIRM
    assert record.profession_type == ProfessionType.CHARTERED_ACCOUNTANT
    assert (record.city, record.state, record.pincode) == ("Testville", "Maharashtra", "411001")
    assert record.phone == "099999 00000"
    assert record.email is None
    assert record.source_url == "https://maps.example.test/1"
    assert record.attributes == {
        "website": "https://firm1.example.com/",
        "latitude": "12.5",
        "longitude": "77.5",
        "google_place_id": "place-1",
        "google_types": "accounting;point_of_interest",
    }


def test_fetch_time_is_not_part_of_the_record_so_reimports_do_not_look_like_changes():
    first = to_registration(row(1, fetched_at="2026-11-03T10:00:00"))
    later = to_registration(row(1, fetched_at="2026-12-09T08:00:00"))

    assert first == later


@pytest.mark.parametrize(
    "category,expected",
    [
        ("tax_consultant", ProfessionType.TAX_CONSULTANT),
        ("financial_planner", ProfessionType.LISTED_FINANCIAL_PLANNER),
        ("investment_advisor", ProfessionType.LISTED_INVESTMENT_ADVISOR),
        ("insurance_advisor", ProfessionType.INSURANCE_ADVISOR),
        ("wealth_manager", ProfessionType.WEALTH_MANAGER),
        ("estate_planner", ProfessionType.ESTATE_PLANNER),
    ],
)
def test_categories_map_to_profession_types_and_listed_types_are_not_the_sebi_ones(category, expected):
    record = to_registration(row(1, category=category))

    assert record.profession_type == expected
    assert record.profession_type != ProfessionType.INVESTMENT_ADVISER


@pytest.mark.parametrize(
    "overrides",
    [{"place_id": ""}, {"name": "  "}, {"category": "astrologer"}, {"category": ""}],
)
def test_unusable_rows_raise_parse_error(overrides):
    with pytest.raises(ParseError):
        to_registration(row(1, **overrides))


@pytest.mark.parametrize(
    "address,state,pincode",
    [
        ("12 Road, Pune, Maharashtra 411001, India", "Maharashtra", "411001"),
        ("Shop 4, Bengaluru, Karnataka 560 001, India", "Karnataka", "560001"),
        ("Somewhere, New Delhi, Delhi 110001", "Delhi", "110001"),
        ("12 Road, Nowhere", None, None),
        ("", None, None),
        (None, None, None),
    ],
)
def test_google_style_addresses_give_state_and_pincode(address, state, pincode):
    assert parse_google_address(address) == (state, pincode)


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"business_status": "CLOSED_PERMANENTLY"}, "permanently closed"),
        ({"name": "Ace Commerce Coaching Classes"}, "name looks like"),
        ({"name": "Tally Software Solutions"}, "name looks like"),
        ({"types": "school;point_of_interest"}, "irrelevant place type: school"),
    ],
)
def test_noise_is_filtered_with_a_reason(overrides, reason):
    assert reason in rejection_reason(row(1, **overrides))


def test_genuine_rows_are_not_filtered_including_temporarily_closed():
    assert rejection_reason(row(1)) is None
    assert rejection_reason(row(2, business_status="CLOSED_TEMPORARILY")) is None


def test_read_csv_separates_kept_rejected_and_broken_rows(tmp_path):
    path = write_csv(
        tmp_path / "places.csv",
        [row(1), row(2, name="Maths Coaching Academy"), row(3, category="astrologer"), row(4, business_status="CLOSED_PERMANENTLY")],
    )

    records, rejected, parse_errors = read_csv(path)

    assert [r.registration_number for r in records] == ["GP-place-1"]
    assert len(rejected) == 2
    assert parse_errors == 1


@pytest.mark.usefixtures("use_test_engine")
async def test_import_stores_unverified_rows_and_lists_the_filtered_ones(engine, tmp_path):
    path = write_csv(tmp_path / "places.csv", [row(1), row(2), row(3, name="Exam Coaching Academy")])

    summary = await load(path)

    assert summary.status == RunStatus.SUCCEEDED
    assert (summary.records_seen, summary.inserted, summary.expected_total) == (2, 2, 2)
    async with AsyncSession(engine) as session:
        source = await session.scalar(select(DataSource).where(DataSource.key == "google_places"))
        registrations = (await session.scalars(select(ProfessionalRegistration))).all()
    assert source.verification_level == "unverified"
    assert {r.registration_number for r in registrations} == {"GP-place-1", "GP-place-2"}
    rejected = (tmp_path / "places.rejected.csv").read_text(encoding="utf-8")
    assert "Exam Coaching Academy" in rejected and "name looks like" in rejected


@pytest.mark.usefixtures("use_test_engine")
async def test_reimport_is_idempotent_and_picks_up_changes(tmp_path):
    path = write_csv(tmp_path / "places.csv", [row(1), row(2)])
    await load(path)

    same = await load(path)
    write_csv(path, [row(1, phone="088888 11111"), row(2)])
    changed = await load(path)

    assert (same.inserted, same.updated, same.unchanged) == (0, 0, 2)
    assert (changed.inserted, changed.updated, changed.unchanged) == (0, 1, 1)


@pytest.mark.usefixtures("use_test_engine")
async def test_rows_missing_from_a_later_file_are_never_delisted(engine, tmp_path):
    path = write_csv(tmp_path / "places.csv", [row(1), row(2)])
    await load(path)
    smaller = write_csv(tmp_path / "second.csv", [row(1)])
    await load(smaller)
    await load(smaller)
    await load(smaller)

    async with AsyncSession(engine) as session:
        rows = (await session.scalars(select(ProfessionalRegistration))).all()
    assert {r.status for r in rows} == {"active"}
    assert {r.missing_runs for r in rows} == {0}


@pytest.mark.usefixtures("use_test_engine")
async def test_a_broken_row_makes_the_run_partial_but_keeps_the_rest(tmp_path):
    path = write_csv(tmp_path / "places.csv", [row(1), row(2, category="astrologer")])

    summary = await load(path)

    assert summary.status == RunStatus.PARTIAL
    assert summary.inserted == 1


@pytest.mark.usefixtures("use_test_engine")
async def test_an_empty_or_fully_filtered_file_imports_nothing(tmp_path):
    path = write_csv(tmp_path / "places.csv", [row(1, name="Coaching Classes")])

    summary = await load(path)

    assert summary.records_seen == 0
    assert summary.inserted == 0
