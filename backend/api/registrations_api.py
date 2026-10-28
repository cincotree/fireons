from datetime import date, datetime
from typing import Annotated, Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, false, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.public_rate_limit import limit_public_reads
from database.models import (
    DataSource,
    FinancialProfessional,
    NriSignal,
    ProfessionalRegistration,
    ProfessionalWebsite,
    RegistrationVersion,
    ScrapeRun,
)
from database.session import get_session
from scraping.normalize import normalize_name
from scraping.types import RunStatus

MAX_PAGE_SIZE = 100
MAX_FILTER_VALUES = 60
MAX_SEARCH_TOKENS = 8
FUZZY_MIN_TOKEN_LENGTH = 4
FUZZY_WORD_SIMILARITY = "0.4"

NRI_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}
NRI_MIN_CONFIDENCES = {
    "high": ["high"],
    "medium": ["high", "medium"],
    "low": ["high", "medium", "low"],
}

MultiValue = Annotated[list[str], Query(max_length=MAX_FILTER_VALUES)]


def _lowered(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values if value.strip()]


router = APIRouter(
    prefix="/registrations",
    tags=["registrations"],
    dependencies=[Depends(limit_public_reads)],
)


class NriSummary(BaseModel):
    confidence: str
    signal_count: int
    confirmed: bool
    website_url: Optional[str]


class RegistrationResponse(BaseModel):
    id: str
    professional_id: str
    name: str
    kind: str
    registration_number: str
    profession_type: str
    source_key: str
    source_name: str
    regulator: str
    status: str
    valid_from: Optional[date]
    valid_until: Optional[date]
    validity_raw: Optional[str]
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    address: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    contact_person: Optional[str]
    source_url: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_changed_at: datetime
    nri: Optional[NriSummary] = None


class RegistrationPage(BaseModel):
    items: list[RegistrationResponse]
    total: int
    page: int
    page_size: int


class RunInfo(BaseModel):
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    records_seen: int
    expected_total: Optional[int]


class SourceResponse(BaseModel):
    key: str
    name: str
    regulator: str
    profession_type: str
    total_registrations: int
    last_run: Optional[RunInfo]
    last_success_at: Optional[datetime]


class NriSignalResponse(BaseModel):
    id: str
    page_url: str
    signal_type: str
    matched_text: str
    location: str
    confidence: str
    review_status: str
    last_seen_at: datetime


class NriWebsiteResponse(BaseModel):
    url: str
    domain: str
    derived_from: str
    check_status: str
    pages_checked: int
    last_checked_at: Optional[datetime]


class NriDetailResponse(BaseModel):
    registration_id: str
    website: Optional[NriWebsiteResponse]
    signals: list[NriSignalResponse]


class FacetsResponse(BaseModel):
    states: list[str]
    cities: list[str]
    profession_types: list[str]


class FieldChange(BaseModel):
    field: str
    previous: Any
    current: Any


class VersionResponse(BaseModel):
    id: str
    scraped_at: datetime
    content_hash: str
    is_initial: bool
    changes: list[FieldChange]
    snapshot: dict[str, Any]


class HistoryResponse(BaseModel):
    registration_id: str
    versions: list[VersionResponse]


def _to_response(
    registration: ProfessionalRegistration,
    professional: FinancialProfessional,
    source: DataSource,
) -> RegistrationResponse:
    return RegistrationResponse(
        id=registration.id,
        professional_id=professional.id,
        name=professional.display_name,
        kind=professional.kind,
        registration_number=registration.registration_number,
        profession_type=registration.profession_type,
        source_key=source.key,
        source_name=source.name,
        regulator=source.regulator,
        status=registration.status,
        valid_from=registration.valid_from,
        valid_until=registration.valid_until,
        validity_raw=registration.validity_raw,
        city=registration.city,
        state=registration.state,
        pincode=registration.pincode,
        address=registration.address_raw,
        email=registration.email,
        phone=registration.phone,
        contact_person=registration.contact_person,
        source_url=registration.source_url,
        first_seen_at=registration.first_seen_at,
        last_seen_at=registration.last_seen_at,
        last_changed_at=registration.last_changed_at,
    )


async def _nri_summaries(
    session: AsyncSession, professional_ids: list[str]
) -> dict[str, NriSummary]:
    if not professional_ids:
        return {}
    rows = (
        await session.execute(
            select(
                NriSignal.professional_id,
                NriSignal.confidence,
                NriSignal.review_status,
                ProfessionalWebsite.url,
            )
            .join(ProfessionalWebsite, ProfessionalWebsite.id == NriSignal.website_id)
            .where(
                NriSignal.professional_id.in_(professional_ids),
                NriSignal.review_status != "rejected",
            )
        )
    ).all()
    summaries: dict[str, NriSummary] = {}
    for professional_id, confidence, review_status, website_url in rows:
        current = summaries.get(professional_id)
        if current is None:
            summaries[professional_id] = NriSummary(
                confidence=confidence,
                signal_count=1,
                confirmed=review_status == "confirmed",
                website_url=website_url,
            )
            continue
        current.signal_count += 1
        current.confirmed = current.confirmed or review_status == "confirmed"
        if NRI_CONFIDENCE_RANK[confidence] > NRI_CONFIDENCE_RANK[current.confidence]:
            current.confidence = confidence
    return summaries


def _base_query():
    return (
        select(ProfessionalRegistration, FinancialProfessional, DataSource)
        .join(FinancialProfessional, FinancialProfessional.id == ProfessionalRegistration.professional_id)
        .join(DataSource, DataSource.id == ProfessionalRegistration.source_id)
    )


def _search_fields():
    return [
        FinancialProfessional.name_normalized,
        func.lower(func.coalesce(ProfessionalRegistration.city, "")),
        func.lower(func.coalesce(ProfessionalRegistration.state, "")),
        func.lower(DataSource.name),
    ]


def _token_matches(token: str):
    contains = f"%{token}%"
    fields = _search_fields()
    clauses = [field.like(contains) for field in fields]
    clauses.append(func.lower(ProfessionalRegistration.registration_number).like(contains))
    if len(token) >= FUZZY_MIN_TOKEN_LENGTH:
        clauses.extend(field.op("%>")(token) for field in fields)
    return or_(*clauses)


def _token_score(token: str):
    contains = f"%{token}%"
    similarities = [func.word_similarity(token, field) for field in _search_fields()]
    registration_hit = case(
        (func.lower(ProfessionalRegistration.registration_number).like(contains), 1.0),
        else_=0.0,
    )
    return func.greatest(*similarities, registration_hit)


@router.get("/sources", response_model=list[SourceResponse])
async def list_sources(session: AsyncSession = Depends(get_session)):
    sources = (
        await session.scalars(
            select(DataSource).where(DataSource.is_enabled.is_(True)).order_by(DataSource.name)
        )
    ).all()
    responses = []
    for source in sources:
        total = await session.scalar(
            select(func.count())
            .select_from(ProfessionalRegistration)
            .where(ProfessionalRegistration.source_id == source.id)
        )
        last_run = await session.scalar(
            select(ScrapeRun)
            .where(ScrapeRun.source_id == source.id, ScrapeRun.status != RunStatus.RUNNING.value)
            .order_by(ScrapeRun.started_at.desc())
            .limit(1)
        )
        last_success = await session.scalar(
            select(func.max(ScrapeRun.finished_at)).where(
                ScrapeRun.source_id == source.id, ScrapeRun.status == RunStatus.SUCCEEDED.value
            )
        )
        responses.append(
            SourceResponse(
                key=source.key,
                name=source.name,
                regulator=source.regulator,
                profession_type=source.default_profession_type,
                total_registrations=total or 0,
                last_run=RunInfo(
                    status=last_run.status,
                    started_at=last_run.started_at,
                    finished_at=last_run.finished_at,
                    records_seen=last_run.records_seen,
                    expected_total=last_run.expected_total,
                )
                if last_run
                else None,
                last_success_at=last_success,
            )
        )
    return responses


@router.get("/facets", response_model=FacetsResponse)
async def get_facets(
    source: Optional[str] = None,
    state: MultiValue = [],
    session: AsyncSession = Depends(get_session),
):
    scope = []
    if source:
        scope.append(
            ProfessionalRegistration.source_id.in_(select(DataSource.id).where(DataSource.key == source))
        )
    states_query = (
        select(ProfessionalRegistration.state)
        .where(ProfessionalRegistration.state.is_not(None), *scope)
        .distinct()
        .order_by(ProfessionalRegistration.state)
    )
    cities_scope = list(scope)
    if _lowered(state):
        cities_scope.append(func.lower(ProfessionalRegistration.state).in_(_lowered(state)))
    cities_query = (
        select(ProfessionalRegistration.city)
        .where(ProfessionalRegistration.city.is_not(None), *cities_scope)
        .distinct()
        .order_by(ProfessionalRegistration.city)
    )
    types_query = (
        select(ProfessionalRegistration.profession_type)
        .where(*scope)
        .distinct()
        .order_by(ProfessionalRegistration.profession_type)
    )
    return FacetsResponse(
        states=list((await session.scalars(states_query)).all()),
        cities=list((await session.scalars(cities_query)).all()),
        profession_types=list((await session.scalars(types_query)).all()),
    )


@router.get("", response_model=RegistrationPage)
async def list_registrations(
    source: Optional[str] = None,
    profession_type: Optional[str] = None,
    q: Optional[str] = Query(default=None, max_length=200),
    state: MultiValue = [],
    city: MultiValue = [],
    status: Optional[Literal["active", "expired", "delisted"]] = None,
    nri: Optional[Literal["high", "medium", "low"]] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=MAX_PAGE_SIZE),
    session: AsyncSession = Depends(get_session),
):
    conditions = []
    if source:
        conditions.append(DataSource.key == source)
    if profession_type:
        conditions.append(ProfessionalRegistration.profession_type == profession_type)
    if status:
        conditions.append(ProfessionalRegistration.status == status)
    if _lowered(state):
        conditions.append(func.lower(ProfessionalRegistration.state).in_(_lowered(state)))
    if _lowered(city):
        conditions.append(func.lower(ProfessionalRegistration.city).in_(_lowered(city)))

    if nri:
        conditions.append(
            select(NriSignal.id)
            .where(
                NriSignal.professional_id == ProfessionalRegistration.professional_id,
                NriSignal.review_status != "rejected",
                NriSignal.confidence.in_(NRI_MIN_CONFIDENCES[nri]),
            )
            .exists()
        )

    ranking = []
    if q and q.strip():
        tokens = normalize_name(q).split()[:MAX_SEARCH_TOKENS]
        if not tokens:
            conditions.append(false())
        else:
            await session.execute(
                text("SELECT set_config('pg_trgm.word_similarity_threshold', :value, true)"),
                {"value": FUZZY_WORD_SIMILARITY},
            )
            conditions.extend(_token_matches(token) for token in tokens)
            ranking = [sum(_token_score(token) for token in tokens).desc()]

    total = await session.scalar(
        select(func.count())
        .select_from(ProfessionalRegistration)
        .join(FinancialProfessional, FinancialProfessional.id == ProfessionalRegistration.professional_id)
        .join(DataSource, DataSource.id == ProfessionalRegistration.source_id)
        .where(*conditions)
    )
    rows = await session.execute(
        _base_query()
        .where(*conditions)
        .order_by(
            *ranking,
            FinancialProfessional.name_normalized,
            ProfessionalRegistration.registration_number,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    results = rows.all()
    summaries = await _nri_summaries(session, [row[1].id for row in results])
    items = []
    for row in results:
        item = _to_response(*row)
        item.nri = summaries.get(row[1].id)
        items.append(item)
    return RegistrationPage(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def _load_registration(session: AsyncSession, registration_id: str):
    try:
        UUID(registration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Registration not found")
    row = (
        await session.execute(
            _base_query().where(ProfessionalRegistration.id == registration_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    return row


@router.get("/{registration_id}", response_model=RegistrationResponse)
async def get_registration(registration_id: str, session: AsyncSession = Depends(get_session)):
    return _to_response(*await _load_registration(session, registration_id))


@router.get("/{registration_id}/nri", response_model=NriDetailResponse)
async def get_registration_nri(registration_id: str, session: AsyncSession = Depends(get_session)):
    registration, professional, _ = await _load_registration(session, registration_id)
    website = await session.scalar(
        select(ProfessionalWebsite)
        .where(ProfessionalWebsite.professional_id == professional.id)
        .order_by(ProfessionalWebsite.domain)
        .limit(1)
    )
    signals = (
        await session.scalars(
            select(NriSignal)
            .where(NriSignal.professional_id == professional.id, NriSignal.review_status != "rejected")
        )
    ).all()
    signals = sorted(
        signals, key=lambda signal: (-NRI_CONFIDENCE_RANK[signal.confidence], signal.page_url)
    )
    return NriDetailResponse(
        registration_id=registration.id,
        website=NriWebsiteResponse(
            url=website.url,
            domain=website.domain,
            derived_from=website.derived_from,
            check_status=website.check_status,
            pages_checked=website.pages_checked,
            last_checked_at=website.last_checked_at,
        )
        if website
        else None,
        signals=[
            NriSignalResponse(
                id=signal.id,
                page_url=signal.page_url,
                signal_type=signal.signal_type,
                matched_text=signal.matched_text,
                location=signal.location,
                confidence=signal.confidence,
                review_status=signal.review_status,
                last_seen_at=signal.last_seen_at,
            )
            for signal in signals
        ],
    )


@router.get("/{registration_id}/history", response_model=HistoryResponse)
async def get_registration_history(
    registration_id: str, session: AsyncSession = Depends(get_session)
):
    registration, _, _ = await _load_registration(session, registration_id)
    versions = (
        await session.scalars(
            select(RegistrationVersion)
            .where(RegistrationVersion.registration_id == registration.id)
            .order_by(RegistrationVersion.scraped_at.asc(), RegistrationVersion.id)
        )
    ).all()
    responses: list[VersionResponse] = []
    previous: dict[str, Any] | None = None
    for version in versions:
        changes = []
        if previous is not None:
            for field in sorted(set(previous) | set(version.snapshot)):
                if previous.get(field) != version.snapshot.get(field):
                    changes.append(
                        FieldChange(
                            field=field,
                            previous=previous.get(field),
                            current=version.snapshot.get(field),
                        )
                    )
        responses.append(
            VersionResponse(
                id=version.id,
                scraped_at=version.scraped_at,
                content_hash=version.content_hash,
                is_initial=previous is None,
                changes=changes,
                snapshot=version.snapshot,
            )
        )
        previous = version.snapshot
    responses.reverse()
    return HistoryResponse(registration_id=registration.id, versions=responses)
