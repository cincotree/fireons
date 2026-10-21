import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app import create_app
from app_config import AppSettings

APP_ORIGIN = "https://app.fireons.com"


def _client(**overrides) -> AsyncClient:
    values = {"secret_key": "k" * 32, "cors_origins": APP_ORIGIN}
    values.update(overrides)
    app = create_app(AppSettings(_env_file=None, **values))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_missing_secret_key_fails(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError, match="secret_key"):
        AppSettings(_env_file=None)


async def _preflight(client: AsyncClient, origin: str):
    return await client.options(
        "/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )


@pytest.mark.asyncio
async def test_cors_origins_come_from_settings():
    async with _client() as client:
        allowed = await _preflight(client, APP_ORIGIN)
        rejected = await _preflight(client, "http://localhost:3000")

    assert allowed.headers["access-control-allow-origin"] == APP_ORIGIN
    assert rejected.status_code == 400


@pytest.mark.asyncio
async def test_debug_routes_can_be_disabled():
    async with _client(ingestion_test_enabled=False, api_docs_enabled=False) as client:
        ingestion_test = await client.post("/api/ingestion-test/upload")
        docs = await client.get("/openapi.json")

    assert ingestion_test.status_code == 404
    assert docs.status_code == 404
