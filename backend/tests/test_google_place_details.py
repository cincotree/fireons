from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from api import registrations_api
from api.google_place_details import PlaceDetailsUnavailable, fetch_place_details
from app import app
from app_config import AppSettings, get_app_settings
from database.models import DataSource
from tests.test_registrations_api import add_registration, anonymous_client, client  # noqa: F401


def transport_returning(status_code: int, body: dict | None = None, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status_code, json=body or {})

    return httpx.MockTransport(handler)


async def test_details_request_asks_only_for_name_address_and_maps_link():
    seen: list[httpx.Request] = []
    body = {
        "displayName": {"text": "Sample Advisers", "languageCode": "en"},
        "formattedAddress": "1 Test Road, Testville",
        "googleMapsUri": "https://maps.example.test/x",
    }

    details = await fetch_place_details("key-1", "place-1", transport_returning(200, body, seen))

    assert (details.name, details.address, details.maps_url) == (
        "Sample Advisers",
        "1 Test Road, Testville",
        "https://maps.example.test/x",
    )
    request = seen[0]
    assert request.url.path == "/v1/places/place-1"
    assert request.headers["X-Goog-FieldMask"] == "displayName,formattedAddress,googleMapsUri"
    assert request.headers["X-Goog-Api-Key"] == "key-1"
    assert "key-1" not in str(request.url)


async def test_missing_fields_come_back_empty():
    details = await fetch_place_details("key-1", "place-1", transport_returning(200, {}))

    assert (details.name, details.address, details.maps_url) == (None, None, None)


async def test_missing_key_is_unavailable():
    with pytest.raises(PlaceDetailsUnavailable):
        await fetch_place_details("", "place-1", transport_returning(200))


@pytest.mark.parametrize("status_code", [403, 404, 429, 500])
async def test_google_errors_are_unavailable(status_code):
    with pytest.raises(PlaceDetailsUnavailable):
        await fetch_place_details("key-1", "place-1", transport_returning(status_code))


async def test_network_failure_is_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("slow")

    with pytest.raises(PlaceDetailsUnavailable):
        await fetch_place_details("key-1", "place-1", httpx.MockTransport(handler))


@pytest_asyncio.fixture
async def google_listing(session):
    source = DataSource(
        key="google_places",
        name="Google Maps business listings",
        regulator="Google Maps",
        default_profession_type="chartered_accountant",
        base_url="https://www.google.com/maps",
        verification_level="unverified",
    )
    session.add(source)
    await session.flush()
    return await add_registration(
        session,
        source,
        "Google Maps listing",
        "GP-place-1",
        address_raw=None,
        email=None,
        phone=None,
        attributes={"google_place_id": "place-1"},
    )


@pytest.fixture
def google_key():
    app.dependency_overrides[get_app_settings] = lambda: AppSettings(secret_key="x", google_api_key="key-1")
    yield
    app.dependency_overrides.pop(get_app_settings, None)


async def test_listing_response_carries_the_place_id_and_no_google_content(client, google_listing):
    body = (await client.get(f"/registrations/{google_listing.id}")).json()

    assert body["google_place_id"] == "place-1"
    assert body["address"] is None and body["phone"] is None and body["email"] is None


async def test_endpoint_returns_live_details(client, google_listing, google_key, monkeypatch):
    calls = []

    async def fake_fetch(api_key, place_id, transport=None):
        calls.append((api_key, place_id))
        return registrations_api.GooglePlaceDetails(name="Live Name", address="Live Address", maps_url="https://maps.example.test/x")

    monkeypatch.setattr(registrations_api, "fetch_place_details", fake_fetch)

    response = await client.get(f"/registrations/{google_listing.id}/google")

    assert response.status_code == 200
    assert response.json() == {"name": "Live Name", "address": "Live Address", "maps_url": "https://maps.example.test/x"}
    assert calls == [("key-1", "place-1")]


async def test_endpoint_is_502_when_google_is_unavailable(client, google_listing, google_key, monkeypatch):
    async def failing_fetch(api_key, place_id, transport=None):
        raise PlaceDetailsUnavailable("Google returned 429")

    monkeypatch.setattr(registrations_api, "fetch_place_details", failing_fetch)

    response = await client.get(f"/registrations/{google_listing.id}/google")

    assert response.status_code == 502


async def test_endpoint_is_404_for_a_register_row(client, session, google_key):
    source = DataSource(
        key="sebi_ria",
        name="SEBI Registered Investment Advisers",
        regulator="SEBI",
        default_profession_type="investment_adviser",
        base_url="https://example.test",
        verification_level="verified",
    )
    session.add(source)
    await session.flush()
    registration = await add_registration(session, source, "Rohan Mehta", "INA000000001")

    response = await client.get(f"/registrations/{registration.id}/google")

    assert response.status_code == 404


@pytest.mark.parametrize("registration_id", ["not-a-uuid", str(uuid4())])
async def test_endpoint_is_404_for_unknown_registration(client, registration_id):
    response = await client.get(f"/registrations/{registration_id}/google")

    assert response.status_code == 404


async def test_endpoint_requires_a_signed_in_user(anonymous_client, google_listing):
    response = await anonymous_client.get(f"/registrations/{google_listing.id}/google")

    assert response.status_code in {401, 403}
