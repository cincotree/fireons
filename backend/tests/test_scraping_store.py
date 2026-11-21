from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from database.models import (
    FinancialProfessional,
    ProfessionalRegistration,
    RegistrationVersion,
    ScrapeRun,
)
from scraping.sources.sebi_ria import DEFINITION, parse_listing_page
from scraping.store import ensure_data_source, mark_unseen_registrations, upsert_registrations
from scraping.types import RegistrationStatus
from tests.fixtures.generate_sebi_fixtures import FIXTURES_DIR
from tests.test_scraping_normalize import make_record

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 1, 1)


@pytest_asyncio.fixture
async def source(session):
    return await ensure_data_source(session, DEFINITION)


@pytest_asyncio.fixture
async def run(session, source):
    scrape_run = ScrapeRun(source_id=source.id, trigger="manual", status="running", started_at=T0)
    session.add(scrape_run)
    await session.flush()
    return scrape_run


async def count(session, model) -> int:
    return await session.scalar(select(func.count()).select_from(model))


def fixture_records():
    return parse_listing_page((FIXTURES_DIR / "listing_page_1.html").read_text()).records


async def test_new_records_create_professional_registration_and_first_version(session, source, run):
    counts = await upsert_registrations(session, source, run.id, fixture_records(), T0, TODAY)

    assert (counts.inserted, counts.updated, counts.unchanged) == (3, 0, 0)
    assert await count(session, FinancialProfessional) == 3
    assert await count(session, ProfessionalRegistration) == 3
    assert await count(session, RegistrationVersion) == 3


async def test_rerunning_identical_data_is_a_noop_except_last_seen(session, source, run):
    await upsert_registrations(session, source, run.id, fixture_records(), T0, TODAY)
    later = T0 + timedelta(days=7)
    next_run = ScrapeRun(source_id=source.id, trigger="scheduled", status="running", started_at=later)
    session.add(next_run)
    await session.flush()

    counts = await upsert_registrations(session, source, next_run.id, fixture_records(), later, TODAY)

    assert (counts.inserted, counts.updated, counts.unchanged) == (0, 0, 3)
    assert await count(session, FinancialProfessional) == 3
    assert await count(session, RegistrationVersion) == 3
    registrations = (await session.scalars(select(ProfessionalRegistration))).all()
    assert all(r.last_seen_at == later for r in registrations)
    assert all(r.last_changed_at == T0 for r in registrations)
    assert all(r.first_seen_at == T0 for r in registrations)


async def test_changed_record_updates_row_and_appends_version(session, source, run):
    original = make_record()
    await upsert_registrations(session, source, run.id, [original], T0, TODAY)
    later = T0 + timedelta(days=7)
    next_run = ScrapeRun(source_id=source.id, trigger="scheduled", status="running", started_at=later)
    session.add(next_run)
    await session.flush()

    changed = make_record(email="new@example.com", phone="919999999999")
    counts = await upsert_registrations(session, source, next_run.id, [changed], later, TODAY)

    assert (counts.inserted, counts.updated, counts.unchanged) == (0, 1, 0)
    registration = await session.scalar(select(ProfessionalRegistration))
    assert registration.email == "new@example.com"
    assert registration.phone == "919999999999"
    assert registration.last_changed_at == later
    assert registration.first_seen_at == T0
    versions = (
        await session.scalars(select(RegistrationVersion).order_by(RegistrationVersion.scraped_at))
    ).all()
    assert [v.snapshot["email"] for v in versions] == ["a@example.com", "new@example.com"]


async def test_name_change_updates_single_registration_professional(session, source, run):
    await upsert_registrations(session, source, run.id, [make_record()], T0, TODAY)
    later = T0 + timedelta(days=1)
    next_run = ScrapeRun(source_id=source.id, trigger="scheduled", status="running", started_at=later)
    session.add(next_run)
    await session.flush()

    await upsert_registrations(
        session, source, next_run.id, [make_record(name="Renamed Adviser")], later, TODAY
    )

    professional = await session.scalar(select(FinancialProfessional))
    assert professional.display_name == "Renamed Adviser"
    assert professional.name_normalized == "renamed adviser"
    assert await count(session, FinancialProfessional) == 1


async def test_status_is_derived_from_validity_end_date(session, source, run):
    expired = make_record(
        registration_number="INA000000002", valid_until=date(2024, 3, 4), validity_raw="x"
    )
    perpetual = make_record()

    await upsert_registrations(session, source, run.id, [expired, perpetual], T0, TODAY)

    rows = {
        r.registration_number: r.status for r in (await session.scalars(select(ProfessionalRegistration))).all()
    }
    assert rows == {
        "INA000000001": RegistrationStatus.ACTIVE.value,
        "INA000000002": RegistrationStatus.EXPIRED.value,
    }


async def test_same_number_in_different_sources_is_kept_separate(session, source, run):
    from scraping.types import ProfessionType, SourceDefinition

    other = await ensure_data_source(
        session,
        SourceDefinition("other_source", "Other", "AMFI", ProfessionType.MF_DISTRIBUTOR, "https://other.test"),
    )
    other_run = ScrapeRun(source_id=other.id, trigger="manual", status="running", started_at=T0)
    session.add(other_run)
    await session.flush()

    await upsert_registrations(session, source, run.id, [make_record()], T0, TODAY)
    await upsert_registrations(session, other, other_run.id, [make_record()], T0, TODAY)

    assert await count(session, ProfessionalRegistration) == 2


async def test_unseen_registrations_are_delisted_only_after_consecutive_misses(session, source, run):
    keeper = make_record()
    leaver = make_record(registration_number="INA000000009", name="Leaving Adviser")
    await upsert_registrations(session, source, run.id, [keeper, leaver], T0, TODAY)

    for week in (1, 2):
        started = T0 + timedelta(days=7 * week)
        week_run = ScrapeRun(source_id=source.id, trigger="scheduled", status="running", started_at=started)
        session.add(week_run)
        await session.flush()
        await upsert_registrations(session, source, week_run.id, [keeper], started, TODAY)
        delisted = await mark_unseen_registrations(session, source, started, delist_after=2)
        leaving = await session.scalar(
            select(ProfessionalRegistration).where(
                ProfessionalRegistration.registration_number == "INA000000009"
            )
        )
        await session.refresh(leaving)
        if week == 1:
            assert delisted == 0
            assert leaving.missing_runs == 1
            assert leaving.status == RegistrationStatus.ACTIVE.value
        else:
            assert delisted == 1
            assert leaving.status == RegistrationStatus.DELISTED.value

    kept = await session.scalar(
        select(ProfessionalRegistration).where(ProfessionalRegistration.registration_number == "INA000000001")
    )
    assert kept.status == RegistrationStatus.ACTIVE.value
    assert kept.missing_runs == 0


async def test_delisted_registration_reactivates_when_it_reappears(session, source, run):
    record = make_record()
    await upsert_registrations(session, source, run.id, [record], T0, TODAY)
    registration = await session.scalar(select(ProfessionalRegistration))
    registration.status = RegistrationStatus.DELISTED.value
    registration.missing_runs = 2
    await session.flush()
    later = T0 + timedelta(days=30)
    next_run = ScrapeRun(source_id=source.id, trigger="scheduled", status="running", started_at=later)
    session.add(next_run)
    await session.flush()

    await upsert_registrations(session, source, next_run.id, [record], later, TODAY)

    await session.refresh(registration)
    assert registration.status == RegistrationStatus.ACTIVE.value
    assert registration.missing_runs == 0
