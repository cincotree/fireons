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
async def test_ingestion_test_router_can_be_disabled():
    async with _client(ingestion_test_enabled=False) as client:
        response = await client.post("/api/ingestion-test/upload")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ingestion_endpoints_return_503_when_disabled():
    async with _client(ingestion_enabled=False) as client:
        check = await client.post("/api/ingestion/check")
        upload = await client.post("/api/ingestion/upload")
        run = await client.get("/api/ingestion/runs/abc")

    assert check.status_code == 503
    assert upload.status_code == 503
    assert run.status_code == 503


@pytest.mark.asyncio
async def test_ingestion_pipeline_is_not_imported_when_disabled():
    import subprocess
    import sys

    code = (
        "import sys;"
        "from app import create_app;"
        "from app_config import AppSettings;"
        "create_app(AppSettings(_env_file=None, secret_key='k'*32, ingestion_enabled=False, ingestion_test_enabled=False));"
        "bad=[m for m in ('anthropic','pypdf','ingestion.pipeline') if m in sys.modules];"
        "print(bad)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={
            "PATH": "",
            "SECRET_KEY": "k" * 32,
            "DATABASE_URL": "postgresql+psycopg://x:x@localhost/x",
            "INGESTION_ENABLED": "false",
            "INGESTION_TEST_ENABLED": "false",
        },
    )

    assert result.stdout.strip() == "[]", result.stderr


@pytest.mark.asyncio
async def test_health_does_not_need_database():
    async with _client() as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
