from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api import public_rate_limit
from app import app
from database.models import (
    DataSource,
    FinancialProfessional,
    ProfessionalRegistration,
    RegistrationVersion,
    ScrapeRun,
)
from database.session import get_session
from scraping.normalize import normalize_name

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def client(session):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    public_rate_limit.public_read_limiter.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    public_rate_limit.public_read_limiter.reset()


async def add_registration(session, source, name, number, **overrides):
    professional = FinancialProfessional(
        display_name=name, name_normalized=normalize_name(name), kind="individual"
    )
    session.add(professional)
    await session.flush()
    values = dict(
        professional_id=professional.id,
        source_id=source.id,
        profession_type="investment_adviser",
        registration_number=number,
        status="active",
        valid_from=date(2022, 1, 1),
        valid_until=None,
        validity_raw="Jan 01, 2022 - Perpetual",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
        address_raw="1 Road, Mumbai, Maharashtra, 400001",
        email="x@example.com",
        phone="910000000000",
        contact_person=name,
        attributes={},
        source_url="https://example.test/list",
        content_hash=uuid4().hex + uuid4().hex[:32],
        first_seen_at=T0,
        last_seen_at=T0,
        last_changed_at=T0,
        missing_runs=0,
    )
    values.update(overrides)
    registration = ProfessionalRegistration(**values)
    session.add(registration)
    await session.flush()
    return registration


@pytest_asyncio.fixture
async def source(session):
    data_source = DataSource(
        key="sebi_ria",
        name="SEBI Registered Investment Advisers",
        regulator="SEBI",
        default_profession_type="investment_adviser",
        base_url="https://example.test/list",
    )
    session.add(data_source)
    await session.flush()
    return data_source


@pytest_asyncio.fixture
async def seeded(session, source):
    rows = {
        "mehta": await add_registration(session, source, "Rohan Mehta", "INA000000010"),
        "shah": await add_registration(
            session, source, "Priya Shah", "INA000000011", city="Ahmedabad", state="Gujarat"
        ),
        "mehta_firm": await add_registration(
            session, source, "Mehta & Sons Advisory LLP", "INA000000012", city="Pune"
        ),
        "old": await add_registration(
            session, source, "Old Timer", "INA000000013", status="expired", valid_until=date(2024, 1, 1)
        ),
        "gone": await add_registration(session, source, "Gone Adviser", "INA000000014", status="delisted"),
    }
    return rows


async def test_list_is_public_and_sorted_by_name(client, seeded):
    response = await client.get("/registrations")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert [item["name"] for item in body["items"]] == [
        "Gone Adviser",
        "Mehta & Sons Advisory LLP",
        "Old Timer",
        "Priya Shah",
        "Rohan Mehta",
    ]
    first = body["items"][0]
    assert first["source_key"] == "sebi_ria"
    assert first["regulator"] == "SEBI"
    assert first["profession_type"] == "investment_adviser"
    assert first["email"] == "x@example.com"


async def test_search_matches_name_substring_case_insensitively(client, seeded):
    response = await client.get("/registrations", params={"q": "MEHTA"})

    assert {i["registration_number"] for i in response.json()["items"]} == {
        "INA000000010",
        "INA000000012",
    }


async def test_search_ignores_punctuation_in_names(client, seeded):
    response = await client.get("/registrations", params={"q": "mehta & sons"})

    assert [i["registration_number"] for i in response.json()["items"]] == ["INA000000012"]


async def test_search_matches_registration_number_prefix(client, seeded):
    response = await client.get("/registrations", params={"q": "ina000000011"})

    assert [i["name"] for i in response.json()["items"]] == ["Priya Shah"]


async def test_search_treats_wildcards_literally(client, seeded):
    response = await client.get("/registrations", params={"q": "%"})

    assert response.json()["total"] == 0


async def test_filters_by_state_city_status_and_type(client, seeded):
    by_state = await client.get("/registrations", params={"state": "gujarat"})
    by_city = await client.get("/registrations", params={"city": "PUNE"})
    by_partial_city = await client.get("/registrations", params={"city": "pun"})
    by_status = await client.get("/registrations", params={"status": "expired"})
    by_type = await client.get("/registrations", params={"profession_type": "research_analyst"})
    by_source = await client.get("/registrations", params={"source": "nope"})

    assert [i["name"] for i in by_state.json()["items"]] == ["Priya Shah"]
    assert [i["name"] for i in by_city.json()["items"]] == ["Mehta & Sons Advisory LLP"]
    assert by_partial_city.json()["total"] == 0
    assert [i["name"] for i in by_status.json()["items"]] == ["Old Timer"]
    assert by_type.json()["total"] == 0
    assert by_source.json()["total"] == 0


async def test_pagination_returns_slices_and_total(client, seeded):
    first = await client.get("/registrations", params={"page": 1, "page_size": 2})
    last = await client.get("/registrations", params={"page": 3, "page_size": 2})

    assert first.json()["total"] == 5
    assert len(first.json()["items"]) == 2
    assert len(last.json()["items"]) == 1
    assert last.json()["page"] == 3


@pytest.mark.parametrize(
    "params",
    [{"page_size": 101}, {"page_size": 0}, {"page": 0}, {"status": "weird"}, {"q": "x" * 201}],
)
async def test_invalid_query_parameters_are_rejected(client, seeded, params):
    response = await client.get("/registrations", params=params)

    assert response.status_code == 422


async def test_detail_returns_registration_or_404(client, seeded):
    found = await client.get(f"/registrations/{seeded['shah'].id}")
    missing = await client.get(f"/registrations/{uuid4()}")
    malformed = await client.get("/registrations/not-a-uuid")

    assert found.status_code == 200
    assert found.json()["city"] == "Ahmedabad"
    assert missing.status_code == 404
    assert malformed.status_code == 404


async def test_history_lists_versions_newest_first_with_field_changes(client, session, source, seeded):
    registration = seeded["mehta"]
    run = ScrapeRun(source_id=source.id, trigger="manual", status="succeeded", started_at=T0)
    run2 = ScrapeRun(source_id=source.id, trigger="manual", status="succeeded", started_at=T0 + timedelta(days=7))
    session.add_all([run, run2])
    await session.flush()
    session.add_all(
        [
            RegistrationVersion(
                registration_id=registration.id,
                run_id=run.id,
                scraped_at=T0,
                content_hash="a" * 64,
                snapshot={"email": "old@example.com", "phone": "1", "city": "Mumbai"},
            ),
            RegistrationVersion(
                registration_id=registration.id,
                run_id=run2.id,
                scraped_at=T0 + timedelta(days=7),
                content_hash="b" * 64,
                snapshot={"email": "new@example.com", "phone": "1", "city": "Mumbai"},
            ),
        ]
    )
    await session.flush()

    response = await client.get(f"/registrations/{registration.id}/history")

    assert response.status_code == 200
    versions = response.json()["versions"]
    assert [v["is_initial"] for v in versions] == [False, True]
    assert versions[0]["changes"] == [
        {"field": "email", "previous": "old@example.com", "current": "new@example.com"}
    ]
    assert versions[1]["changes"] == []


async def test_history_404_for_unknown_registration(client, seeded):
    response = await client.get(f"/registrations/{uuid4()}/history")

    assert response.status_code == 404


async def test_sources_endpoint_reports_totals_and_last_run(client, session, source, seeded):
    session.add(
        ScrapeRun(
            source_id=source.id,
            trigger="scheduled",
            status="succeeded",
            started_at=T0,
            finished_at=T0 + timedelta(minutes=3),
            records_seen=5,
            expected_total=5,
        )
    )
    await session.flush()

    response = await client.get("/registrations/sources")

    assert response.status_code == 200
    [entry] = response.json()
    assert entry["key"] == "sebi_ria"
    assert entry["total_registrations"] == 5
    assert entry["last_run"]["status"] == "succeeded"
    assert entry["last_run"]["records_seen"] == 5
    assert entry["last_success_at"] is not None


async def test_sources_endpoint_handles_a_source_that_never_ran(client, source):
    response = await client.get("/registrations/sources")

    [entry] = response.json()
    assert entry["last_run"] is None
    assert entry["last_success_at"] is None
    assert entry["total_registrations"] == 0


async def test_facets_list_distinct_states_cities_and_types(client, seeded):
    response = await client.get("/registrations/facets", params={"source": "sebi_ria"})

    assert response.json() == {
        "states": ["Gujarat", "Maharashtra"],
        "cities": ["Ahmedabad", "Mumbai", "Pune"],
        "profession_types": ["investment_adviser"],
    }


async def test_facet_cities_are_scoped_to_the_selected_state(client, seeded):
    response = await client.get(
        "/registrations/facets", params={"source": "sebi_ria", "state": "maharashtra"}
    )

    assert response.json()["cities"] == ["Mumbai", "Pune"]


async def test_state_and_city_filters_accept_several_values(client, seeded):
    two_states = await client.get(
        "/registrations", params={"state": ["Gujarat", "maharashtra"], "page_size": 50}
    )
    two_cities = await client.get("/registrations", params={"city": ["Mumbai", "Ahmedabad"]})
    states_and_city = await client.get(
        "/registrations", params={"state": ["Maharashtra", "Gujarat"], "city": ["Pune"]}
    )

    assert two_states.json()["total"] == 5
    assert (await client.get("/registrations", params={"state": ["Gujarat"]})).json()["total"] == 1
    assert {i["name"] for i in two_cities.json()["items"]} == {
        "Rohan Mehta",
        "Priya Shah",
        "Old Timer",
        "Gone Adviser",
    }
    assert [i["name"] for i in states_and_city.json()["items"]] == ["Mehta & Sons Advisory LLP"]


async def test_blank_filter_values_are_ignored(client, seeded):
    response = await client.get("/registrations", params={"state": ["", "  "], "city": [" "]})

    assert response.json()["total"] == 5


async def test_unknown_filter_values_match_nothing(client, seeded):
    response = await client.get("/registrations", params={"state": ["Atlantis", "Gujarat"], "city": ["Pune"]})

    assert response.json()["total"] == 0


async def test_too_many_filter_values_are_rejected(client, seeded):
    response = await client.get("/registrations", params={"state": [f"State {n}" for n in range(61)]})

    assert response.status_code == 422


async def test_facet_cities_follow_every_selected_state(client, seeded):
    one = await client.get("/registrations/facets", params={"state": ["Gujarat"]})
    both = await client.get("/registrations/facets", params={"state": ["Gujarat", "Maharashtra"]})

    assert one.json()["cities"] == ["Ahmedabad"]
    assert both.json()["cities"] == ["Ahmedabad", "Mumbai", "Pune"]


async def test_filters_combine_with_search(client, seeded):
    in_maharashtra = await client.get("/registrations", params={"q": "mehta", "state": "Maharashtra"})
    in_pune = await client.get("/registrations", params={"q": "mehta", "city": "Pune"})
    nowhere = await client.get("/registrations", params={"q": "mehta", "state": "Gujarat"})

    assert in_maharashtra.json()["total"] == 2
    assert [i["registration_number"] for i in in_pune.json()["items"]] == ["INA000000012"]
    assert nowhere.json()["total"] == 0


async def test_search_tolerates_typos_in_names(client, seeded):
    response = await client.get("/registrations", params={"q": "mehata"})

    assert {i["registration_number"] for i in response.json()["items"]} == {
        "INA000000010",
        "INA000000012",
    }


async def test_search_tolerates_typos_in_locations(client, seeded):
    city_typo = await client.get("/registrations", params={"q": "ahmadabad"})
    state = await client.get("/registrations", params={"q": "gujarat"})

    assert [i["name"] for i in city_typo.json()["items"]] == ["Priya Shah"]
    assert [i["name"] for i in state.json()["items"]] == ["Priya Shah"]


async def test_search_matches_the_source_name(client, seeded):
    by_source = await client.get("/registrations", params={"q": "sebi"})
    source_and_name = await client.get("/registrations", params={"q": "sebi shah"})

    assert by_source.json()["total"] == 5
    assert [i["name"] for i in source_and_name.json()["items"]] == ["Priya Shah"]


async def test_search_combines_name_and_location_words_across_fields(client, seeded):
    response = await client.get("/registrations", params={"q": "mehta mumbai"})

    assert [i["registration_number"] for i in response.json()["items"]] == ["INA000000010"]


async def test_search_matches_part_of_a_registration_number(client, seeded):
    response = await client.get("/registrations", params={"q": "000012"})

    assert [i["registration_number"] for i in response.json()["items"]] == ["INA000000012"]


async def test_exact_matches_rank_above_fuzzy_ones(client, session, source, seeded):
    await add_registration(session, source, "Shaw Kumar", "INA000000020")

    response = await client.get("/registrations", params={"q": "shah"})

    assert [i["name"] for i in response.json()["items"]] == ["Priya Shah", "Shaw Kumar"]


async def test_unrelated_search_returns_nothing(client, seeded):
    response = await client.get("/registrations", params={"q": "zzzzqqqq"})

    assert response.json()["total"] == 0


async def test_short_tokens_do_not_fuzzy_match(client, seeded):
    response = await client.get("/registrations", params={"q": "sha"})

    assert [i["name"] for i in response.json()["items"]] == ["Priya Shah"]


async def test_search_is_bounded_to_a_reasonable_number_of_words(client, seeded):
    response = await client.get("/registrations", params={"q": " ".join(["mehta"] * 30)})

    assert response.status_code == 200
    assert response.json()["total"] == 2


async def test_public_reads_are_rate_limited_per_ip(client, seeded, monkeypatch):
    monkeypatch.setattr(
        public_rate_limit,
        "public_read_limiter",
        public_rate_limit.SlidingWindowLimiter(max_requests=3, window_seconds=60),
    )

    statuses = [(await client.get("/registrations")).status_code for _ in range(5)]
    blocked = await client.get("/registrations")

    assert statuses == [200, 200, 200, 429, 429]
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1


def test_sliding_window_forgets_old_hits():
    now = {"t": 0.0}
    limiter = public_rate_limit.SlidingWindowLimiter(2, 10, clock=lambda: now["t"])

    assert limiter.check("ip") is None
    assert limiter.check("ip") is None
    assert limiter.check("ip") is not None
    now["t"] = 11.0
    assert limiter.check("ip") is None


def test_public_read_limit_defaults_to_240_and_is_configurable(monkeypatch):
    from api.config import ApiSettings

    monkeypatch.delenv("PUBLIC_READ_LIMIT_PER_MINUTE", raising=False)
    assert ApiSettings(_env_file=None).public_read_limit_per_minute == 240

    monkeypatch.setenv("PUBLIC_READ_LIMIT_PER_MINUTE", "7")
    assert ApiSettings(_env_file=None).public_read_limit_per_minute == 7
