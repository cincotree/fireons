import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import app as app_module
from app import create_app
from app_config import AppSettings, ConfigurationError
from database.config import Settings as DatabaseSettings
from jobs.config import ExchangeRateSyncSettings

ORIGIN_SECRET = "cloudfront-shared-secret"
APP_ORIGIN = "https://app.fireons.com"


def _prod_settings(**overrides) -> AppSettings:
    values = {
        "app_env": "production",
        "secret_key": "c" * 64,
        "origin_verify_secret": ORIGIN_SECRET,
        "cors_origins": APP_ORIGIN,
    }
    values.update(overrides)
    return AppSettings(_env_file=None, **values)


def _dev_settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        app_env="development",
        origin_verify_secret="",
        cors_origins="http://localhost:3000,http://localhost:3020",
    )


def _db_settings() -> DatabaseSettings:
    return DatabaseSettings(_env_file=None, database_url="postgresql://app:pw@db.example.com/fireons")


async def _client(application: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=application), base_url="http://test")


@pytest_asyncio.fixture
async def prod_client():
    async with await _client(create_app(_prod_settings(), _db_settings())) as client:
        yield client


@pytest_asyncio.fixture
async def dev_client():
    async with await _client(create_app(_dev_settings(), _db_settings())) as client:
        yield client


def _verified(extra: dict | None = None) -> dict:
    return {"X-Origin-Verify": ORIGIN_SECRET, **(extra or {})}


def test_create_app_fails_fast_without_secret_key():
    with pytest.raises(ConfigurationError, match="SECRET_KEY"):
        create_app(_prod_settings(secret_key=""), _db_settings())


@pytest.mark.asyncio
class TestOriginVerify:
    async def test_request_without_origin_header_is_rejected(self, prod_client: AsyncClient):
        response = await prod_client.post("/api/auth/login", json={})
        assert response.status_code == 403
        assert response.json() == {"detail": "Forbidden"}

    async def test_request_with_wrong_origin_header_is_rejected(self, prod_client: AsyncClient):
        response = await prod_client.post(
            "/api/auth/login", json={}, headers={"X-Origin-Verify": "guessed-secret"}
        )
        assert response.status_code == 403

    async def test_request_with_correct_origin_header_reaches_the_app(self, prod_client: AsyncClient):
        response = await prod_client.post("/api/auth/login", json={}, headers=_verified())
        assert response.status_code == 422

    async def test_health_is_exempt_from_origin_check(self, prod_client: AsyncClient):
        for path in ("/health", "/api/health"):
            response = await prod_client.get(path)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    async def test_origin_check_disabled_when_secret_unset(self, dev_client: AsyncClient):
        response = await dev_client.post("/api/auth/login", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestCorsFromEnvironment:
    async def _preflight(self, client: AsyncClient, origin: str, headers: dict | None = None):
        return await client.options(
            "/api/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                **(headers or {}),
            },
        )

    async def test_configured_origin_is_allowed(self, prod_client: AsyncClient):
        response = await self._preflight(prod_client, APP_ORIGIN, _verified())
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == APP_ORIGIN

    async def test_localhost_origin_is_not_allowed_in_production(self, prod_client: AsyncClient):
        response = await self._preflight(prod_client, "http://localhost:3000", _verified())
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    async def test_localhost_origin_is_allowed_by_default(self, dev_client: AsyncClient):
        response = await self._preflight(dev_client, "http://localhost:3000")
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


@pytest.mark.asyncio
class TestDebugSurfaces:
    async def test_ingestion_test_router_is_not_mounted_in_production(self, prod_client: AsyncClient):
        response = await prod_client.post("/api/ingestion-test/upload", headers=_verified())
        assert response.status_code == 404

    async def test_ingestion_test_router_is_mounted_in_development(self, dev_client: AsyncClient):
        response = await dev_client.post("/api/ingestion-test/upload")
        assert response.status_code in (401, 403)

    async def test_docs_are_disabled_in_production(self, prod_client: AsyncClient):
        for path in ("/docs", "/redoc", "/openapi.json"):
            response = await prod_client.get(path, headers=_verified())
            assert response.status_code == 404, path

    async def test_docs_are_enabled_in_development(self, dev_client: AsyncClient):
        for path in ("/docs", "/openapi.json"):
            response = await dev_client.get(path)
            assert response.status_code == 200, path


@pytest.mark.asyncio
class TestLifespanScheduler:
    async def _run_lifespan(self, monkeypatch, sync_enabled: bool) -> list:
        started = []

        class FakeScheduler:
            def add_job(self, *args, **kwargs):
                pass

            def start(self):
                started.append(self)

            def shutdown(self, wait: bool = True):
                pass

        async def fake_init_db():
            pass

        monkeypatch.setattr(app_module, "init_db", fake_init_db)
        monkeypatch.setattr(app_module, "AsyncIOScheduler", FakeScheduler)
        monkeypatch.setattr(
            app_module,
            "get_exchange_rate_sync_settings",
            lambda: ExchangeRateSyncSettings(_env_file=None, exchange_rate_sync_enabled=sync_enabled),
        )

        application = create_app(_dev_settings(), _db_settings())
        async with app_module.lifespan(application):
            pass
        return started

    async def test_scheduler_does_not_start_when_sync_disabled(self, monkeypatch):
        assert await self._run_lifespan(monkeypatch, sync_enabled=False) == []

    async def test_scheduler_starts_when_sync_enabled(self, monkeypatch):
        assert len(await self._run_lifespan(monkeypatch, sync_enabled=True)) == 1
