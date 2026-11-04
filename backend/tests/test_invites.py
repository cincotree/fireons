from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from app_config import AppSettings, get_app_settings
from database.models import Invite, InviteRedemption, User
from database.session import get_session


def _settings(**overrides) -> AppSettings:
    return AppSettings(_env_file=None, secret_key="k" * 32, **overrides)


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_app_settings] = lambda: _settings(invite_only=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _invite(session: AsyncSession, code: str = "welcome-code", **fields) -> Invite:
    invite = Invite(code=code, max_uses=fields.pop("max_uses", 1), **fields)
    session.add(invite)
    await session.flush()
    return invite


def _registration(code, name="new_person") -> dict:
    payload = {"email": f"{name}@example.com", "username": name, "password": "secret123"}
    if code is not None:
        payload["invite_code"] = code
    return payload


@pytest.mark.asyncio
async def test_registration_info_reports_invite_requirement(client):
    assert (await client.get("/auth/registration")).json() == {"invite_required": True}

    app.dependency_overrides[get_app_settings] = lambda: _settings()
    assert (await client.get("/auth/registration")).json() == {"invite_required": False}


@pytest.mark.asyncio
async def test_register_with_valid_invite_records_the_redemption(client, session):
    invite = await _invite(session)

    response = await client.post("/auth/register", json=_registration("welcome-code"))

    assert response.status_code == 201
    await session.refresh(invite)
    assert invite.use_count == 1
    user = (await session.execute(select(User).where(User.username == "new_person"))).scalar_one()
    redemption = (await session.execute(select(InviteRedemption))).scalar_one()
    assert (redemption.invite_id, redemption.user_id) == (invite.id, user.id)


@pytest.mark.asyncio
async def test_register_requires_a_code_when_invite_only(client, session):
    await _invite(session)

    for code in (None, "", "   "):
        response = await client.post("/auth/register", json=_registration(code))
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired invite code"


@pytest.mark.asyncio
async def test_register_rejects_unknown_code(client, session):
    await _invite(session)

    response = await client.post("/auth/register", json=_registration("not-the-code"))

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_single_use_invite_cannot_be_reused(client, session):
    await _invite(session)

    first = await client.post("/auth/register", json=_registration("welcome-code", "first_user"))
    second = await client.post("/auth/register", json=_registration("welcome-code", "second_user"))

    assert first.status_code == 201
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_multi_use_invite_allows_each_use(client, session):
    await _invite(session, max_uses=2)

    statuses = [
        (await client.post("/auth/register", json=_registration("welcome-code", f"user_{n}"))).status_code
        for n in range(3)
    ]

    assert statuses == [201, 201, 400]


@pytest.mark.asyncio
async def test_revoked_invite_is_rejected(client, session):
    await _invite(session, revoked_at=datetime.now(timezone.utc))

    response = await client.post("/auth/register", json=_registration("welcome-code"))

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_expired_invite_is_rejected(client, session):
    await _invite(session, expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))

    response = await client.post("/auth/register", json=_registration("welcome-code"))

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invite_with_future_expiry_is_accepted(client, session):
    await _invite(session, expires_at=datetime.now(timezone.utc) + timedelta(days=1))

    response = await client.post("/auth/register", json=_registration("welcome-code"))

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_code_is_trimmed(client, session):
    await _invite(session)

    response = await client.post("/auth/register", json=_registration("  welcome-code\n"))

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_failed_registration_does_not_burn_the_invite(client, session):
    invite = await _invite(session)
    session.add(User(email="taken@example.com", username="taken_user", hashed_password="x"))
    await session.flush()

    clash = await client.post("/auth/register", json=_registration("welcome-code", "taken_user"))
    ok = await client.post("/auth/register", json=_registration("welcome-code", "fresh_user"))

    assert clash.status_code == 400
    assert clash.json()["detail"] == "Username already registered"
    assert ok.status_code == 201
    await session.refresh(invite)
    assert invite.use_count == 1


@pytest.mark.asyncio
async def test_register_ignores_invite_code_when_not_invite_only(client):
    app.dependency_overrides[get_app_settings] = lambda: _settings()

    response = await client.post("/auth/register", json=_registration(None))

    assert response.status_code == 201
