import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from database.session import get_session


class BrokenSession:
    async def execute(self, *_args, **_kwargs):
        raise RuntimeError("connection refused")


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ready_returns_200_when_database_answers(client):
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_and_ready_report_the_build_version(client, monkeypatch):
    info = {"version": "abc123", "built_at": "2026-10-31T05:00:00Z"}
    monkeypatch.setattr("api.health_api.get_build_info", lambda: info)

    health = await client.get("/health")
    ready = await client.get("/health/ready")

    assert health.json() == {"status": "ok", **info}
    assert ready.json() == {"status": "ok", **info}


@pytest.mark.asyncio
async def test_health_reports_dev_when_not_built(client):
    response = await client.get("/health")

    assert response.json()["version"] == "dev"


@pytest.mark.asyncio
async def test_ready_returns_503_when_database_is_down():
    async def broken_session():
        yield BrokenSession()

    app.dependency_overrides[get_session] = broken_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
