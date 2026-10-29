import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

import api.auth_api as auth_api
from api.captcha import verify_turnstile
from app import app
from app_config import AppSettings, get_app_settings
from database.session import get_session


def _settings(**overrides) -> AppSettings:
    return AppSettings(_env_file=None, secret_key="k" * 32, **overrides)


def _payload(**overrides) -> dict:
    values = {"email": "captcha@example.com", "username": "captcha_user", "password": "secret123"}
    values.update(overrides)
    return values


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _enable_captcha(monkeypatch, accepted_tokens: set[str]):
    app.dependency_overrides[get_app_settings] = lambda: _settings(captcha_enabled=True, turnstile_secret_key="s")

    async def fake_verify(token, secret):
        assert secret == "s"
        return token in accepted_tokens

    monkeypatch.setattr(auth_api, "verify_turnstile", fake_verify)


@pytest.mark.asyncio
async def test_register_without_captcha_when_disabled(client):
    app.dependency_overrides[get_app_settings] = lambda: _settings()

    response = await client.post("/auth/register", json=_payload())

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_rejects_missing_token_when_enabled(client, monkeypatch):
    _enable_captcha(monkeypatch, {"good"})

    response = await client.post("/auth/register", json=_payload())

    assert response.status_code == 400
    assert response.json()["detail"] == "Captcha verification failed"


@pytest.mark.asyncio
async def test_register_rejects_bad_token_when_enabled(client, monkeypatch):
    _enable_captcha(monkeypatch, {"good"})

    response = await client.post("/auth/register", json=_payload(captcha_token="bad"))

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_accepts_good_token_when_enabled(client, monkeypatch):
    _enable_captcha(monkeypatch, {"good"})

    response = await client.post("/auth/register", json=_payload(captcha_token="good"))

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_failed_captcha_does_not_create_user(client, monkeypatch):
    _enable_captcha(monkeypatch, {"good"})

    await client.post("/auth/register", json=_payload(captcha_token="bad"))
    retry = await client.post("/auth/register", json=_payload(captcha_token="good"))

    assert retry.status_code == 201


def _transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_verify_turnstile_sends_secret_and_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"success": True})

    assert await verify_turnstile("tok", "sec", transport=_transport(handler)) is True
    assert "secret=sec" in seen["body"]
    assert "response=tok" in seen["body"]


@pytest.mark.asyncio
async def test_verify_turnstile_rejects_unsuccessful_response():
    transport = _transport(lambda request: httpx.Response(200, json={"success": False}))

    assert await verify_turnstile("tok", "sec", transport=transport) is False


@pytest.mark.asyncio
async def test_verify_turnstile_fails_closed_on_server_error():
    transport = _transport(lambda request: httpx.Response(500, text="boom"))

    assert await verify_turnstile("tok", "sec", transport=transport) is False


@pytest.mark.asyncio
async def test_verify_turnstile_fails_closed_on_network_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    assert await verify_turnstile("tok", "sec", transport=_transport(handler)) is False


@pytest.mark.asyncio
async def test_verify_turnstile_fails_closed_on_invalid_json():
    transport = _transport(lambda request: httpx.Response(200, text="not json"))

    assert await verify_turnstile("tok", "sec", transport=transport) is False


@pytest.mark.asyncio
async def test_verify_turnstile_rejects_empty_token_without_calling_cloudflare():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call Cloudflare")

    assert await verify_turnstile("", "sec", transport=_transport(handler)) is False
    assert await verify_turnstile(None, "sec", transport=_transport(handler)) is False


def test_enabling_captcha_requires_a_secret():
    with pytest.raises(ValidationError, match="TURNSTILE_SECRET_KEY"):
        _settings(captcha_enabled=True)


def test_captcha_is_off_by_default():
    assert _settings().captcha_enabled is False
