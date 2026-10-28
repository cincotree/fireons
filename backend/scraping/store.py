from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    DataSource,
    FinancialProfessional,
    ProfessionalRegistration,
    RegistrationVersion,
)
from scraping.normalize import content_hash, derive_status, normalize_name, snapshot
from scraping.types import RegistrationStatus, ScrapedRegistration, SourceDefinition


@dataclass
class UpsertCounts:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0


async def ensure_data_source(session: AsyncSession, definition: SourceDefinition) -> DataSource:
    existing = await session.scalar(select(DataSource).where(DataSource.key == definition.key))
    if existing is not None:
        existing.name = definition.name
        existing.regulator = definition.regulator
        existing.default_profession_type = definition.default_profession_type.value
        existing.base_url = definition.base_url
        return existing
    source = DataSource(
        key=definition.key,
        name=definition.name,
        regulator=definition.regulator,
        default_profession_type=definition.default_profession_type.value,
        base_url=definition.base_url,
    )
    session.add(source)
    await session.flush()
    return source


def _apply_fields(registration: ProfessionalRegistration, record: ScrapedRegistration) -> None:
    registration.profession_type = record.profession_type.value
    registration.valid_from = record.valid_from
    registration.valid_until = record.valid_until
    registration.validity_raw = record.validity_raw
    registration.city = record.city
    registration.state = record.state
    registration.pincode = record.pincode
    registration.address_raw = record.address_raw
    registration.email = record.email
    registration.phone = record.phone
    registration.contact_person = record.contact_person
    registration.attributes = record.attributes
    registration.source_url = record.source_url


async def upsert_registrations(
    session: AsyncSession,
    source: DataSource,
    run_id: str,
    records: list[ScrapedRegistration],
    now: datetime,
    today: date,
) -> UpsertCounts:
    counts = UpsertCounts()
    if not records:
        return counts

    numbers = [record.registration_number for record in records]
    existing_rows = await session.scalars(
        select(ProfessionalRegistration).where(
            ProfessionalRegistration.source_id == source.id,
            ProfessionalRegistration.registration_number.in_(numbers),
        )
    )
    existing = {row.registration_number: row for row in existing_rows}

    for record in records:
        digest = content_hash(record)
        status = derive_status(record.valid_until, today).value
        registration = existing.get(record.registration_number)

        if registration is None:
            professional = FinancialProfessional(
                display_name=record.name,
                name_normalized=normalize_name(record.name),
                kind=record.kind.value,
            )
            session.add(professional)
            await session.flush()
            registration = ProfessionalRegistration(
                professional_id=professional.id,
                source_id=source.id,
                registration_number=record.registration_number,
                status=status,
                content_hash=digest,
                first_seen_at=now,
                last_seen_at=now,
                last_changed_at=now,
                missing_runs=0,
            )
            _apply_fields(registration, record)
            session.add(registration)
            await session.flush()
            session.add(
                RegistrationVersion(
                    registration_id=registration.id,
                    run_id=run_id,
                    scraped_at=now,
                    content_hash=digest,
                    snapshot=snapshot(record),
                )
            )
            counts.inserted += 1
            continue

        registration.last_seen_at = now
        registration.missing_runs = 0
        registration.status = status

        if registration.content_hash == digest:
            counts.unchanged += 1
            continue

        _apply_fields(registration, record)
        registration.content_hash = digest
        registration.last_changed_at = now
        await _refresh_professional(session, registration, record)
        session.add(
            RegistrationVersion(
                registration_id=registration.id,
                run_id=run_id,
                scraped_at=now,
                content_hash=digest,
                snapshot=snapshot(record),
            )
        )
        counts.updated += 1

    await session.flush()
    return counts


async def _refresh_professional(
    session: AsyncSession, registration: ProfessionalRegistration, record: ScrapedRegistration
) -> None:
    professional = await session.get(FinancialProfessional, registration.professional_id)
    if professional is None or professional.display_name == record.name:
        return
    registration_count = await session.scalar(
        select(func.count())
        .select_from(ProfessionalRegistration)
        .where(ProfessionalRegistration.professional_id == professional.id)
    )
    if registration_count == 1:
        professional.display_name = record.name
        professional.name_normalized = normalize_name(record.name)
        professional.kind = record.kind.value


async def mark_unseen_registrations(
    session: AsyncSession, source: DataSource, run_started_at: datetime, delist_after: int
) -> int:
    unseen = (
        ProfessionalRegistration.source_id == source.id,
        ProfessionalRegistration.last_seen_at < run_started_at,
        ProfessionalRegistration.status != RegistrationStatus.DELISTED.value,
    )
    await session.execute(
        update(ProfessionalRegistration)
        .where(*unseen)
        .values(missing_runs=ProfessionalRegistration.missing_runs + 1)
    )
    result = await session.execute(
        update(ProfessionalRegistration)
        .where(*unseen, ProfessionalRegistration.missing_runs >= delist_after)
        .values(status=RegistrationStatus.DELISTED.value)
    )
    return result.rowcount or 0
