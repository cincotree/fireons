import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app import create_app
from app_config import AppSettings

ORIGIN_SECRET = "cloudfront-shared-secret"
APP_ORIGIN = "https://app.fireons.com"


def _client(**overrides) -> AsyncClient:
    values = {"secret_key": "k" * 32, "cors_origins": APP_ORIGIN, "origin_verify_secret": ORIGIN_SECRET}
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
            "X-Origin-Verify": ORIGIN_SECRET,
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
async def test_origin_verify_header():
    async with _client() as client:
        missing = await client.post("/api/auth/login", json={})
        wrong = await client.post("/api/auth/login", json={}, headers={"X-Origin-Verify": "guess"})
        correct = await client.post("/api/auth/login", json={}, headers={"X-Origin-Verify": ORIGIN_SECRET})
        health = await client.get("/api/health")

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert correct.status_code == 422
    assert health.status_code == 200


@pytest.mark.asyncio
async def test_debug_routes_can_be_disabled():
    async with _client(origin_verify_secret="", ingestion_test_enabled=False, api_docs_enabled=False) as client:
        ingestion_test = await client.post("/api/ingestion-test/upload")
        docs = await client.get("/openapi.json")

    assert ingestion_test.status_code == 404
    assert docs.status_code == 404
