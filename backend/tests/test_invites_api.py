from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from app_config import AppSettings, get_app_settings
from auth_utils import create_access_token
from database.models import Invite, User
from database.session import get_session
from scripts.create_superadmin import ensure_superadmin


def _settings(**overrides) -> AppSettings:
    return AppSettings(_env_file=None, secret_key="k" * 32, **overrides)


async def _user(session: AsyncSession, name: str, superadmin: bool = False) -> User:
    user = User(
        email=f"{name}@example.com",
        username=name,
        hashed_password="unused",
        is_superadmin=superadmin,
    )
    session.add(user)
    await session.flush()
    return user


def _headers(user: User) -> dict:
    token = create_access_token(data={"sub": user.id, "username": user.username, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_app_settings] = lambda: _settings(invite_only=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin(session: AsyncSession) -> User:
    return await _user(session, "admin_user", superadmin=True)


@pytest_asyncio.fixture
async def member(session: AsyncSession) -> User:
    return await _user(session, "member_user")


async def _create_invite(client: AsyncClient, admin: User, **body) -> dict:
    response = await client.post("/admin/invites", json=body, headers=_headers(admin))
    assert response.status_code == 201, response.text
    return response.json()


def _registration(code, name="new_person", **extra) -> dict:
    payload = {"email": f"{name}@example.com", "username": name, "password": "secret123"}
    if code is not None:
        payload["invite_code"] = code
    payload.update(extra)
    return payload


@pytest.mark.asyncio
async def test_invite_endpoints_require_authentication(client):
    for method, path in [("get", "/admin/invites"), ("post", "/admin/invites")]:
        response = await getattr(client, method)(path)
        assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_invite_endpoints_reject_regular_users(client, member):
    list_response = await client.get("/admin/invites", headers=_headers(member))
    create_response = await client.post("/admin/invites", json={}, headers=_headers(member))
    revoke_response = await client.post(f"/admin/invites/{uuid4()}/revoke", headers=_headers(member))

    assert list_response.status_code == 403
    assert create_response.status_code == 403
    assert revoke_response.status_code == 403


@pytest.mark.asyncio
async def test_superadmin_creates_invite_and_code_is_shown_once(client, admin, session):
    created = await _create_invite(client, admin, label="for Asha", max_uses=2, expires_in_days=7)

    assert created["code"]
    assert created["status"] == "active"
    assert created["label"] == "for Asha"
    assert created["max_uses"] == 2
    assert created["use_count"] == 0

    listed = (await client.get("/admin/invites", headers=_headers(admin))).json()
    assert [item["id"] for item in listed] == [created["id"]]
    assert "code" not in listed[0]

    stored = (await session.execute(select(Invite))).scalar_one()
    assert stored.code_hash != created["code"]
    assert stored.created_by == admin.id


@pytest.mark.asyncio
async def test_invite_creation_validates_input(client, admin):
    for body in [{"max_uses": 0}, {"max_uses": 5000}, {"expires_in_days": 0}, {"label": "x" * 300}]:
        response = await client.post("/admin/invites", json=body, headers=_headers(admin))
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_invite_without_expiry(client, admin):
    created = await _create_invite(client, admin, expires_in_days=None)

    assert created["expires_at"] is None


@pytest.mark.asyncio
async def test_revoke_invite(client, admin):
    created = await _create_invite(client, admin)

    response = await client.post(f"/admin/invites/{created['id']}/revoke", headers=_headers(admin))

    assert response.status_code == 200
    assert response.json()["status"] == "revoked"
    again = await client.post(f"/admin/invites/{created['id']}/revoke", headers=_headers(admin))
    assert again.status_code == 200


@pytest.mark.asyncio
async def test_revoke_unknown_invite_is_404(client, admin):
    response = await client.post(f"/admin/invites/{uuid4()}/revoke", headers=_headers(admin))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_revoke_with_malformed_id_is_422(client, admin):
    response = await client.post("/admin/invites/not-a-uuid/revoke", headers=_headers(admin))

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_registration_info_reports_invite_requirement(client):
    assert (await client.get("/auth/registration")).json() == {"invite_required": True}

    app.dependency_overrides[get_app_settings] = lambda: _settings()
    assert (await client.get("/auth/registration")).json() == {"invite_required": False}


@pytest.mark.asyncio
async def test_register_with_valid_invite(client, admin):
    created = await _create_invite(client, admin)

    response = await client.post("/auth/register", json=_registration(created["code"]))

    assert response.status_code == 201
    assert response.json()["is_superadmin"] is False
    listed = (await client.get("/admin/invites", headers=_headers(admin))).json()[0]
    assert listed["use_count"] == 1
    assert listed["status"] == "exhausted"
    assert listed["redeemed_by"] == ["new_person"]


@pytest.mark.asyncio
async def test_register_requires_a_code_when_invite_only(client):
    for code in (None, "", "   "):
        response = await client.post("/auth/register", json=_registration(code))
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired invite code"


@pytest.mark.asyncio
async def test_register_rejects_unknown_code(client):
    response = await client.post("/auth/register", json=_registration("not-a-real-code"))

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_single_use_invite_cannot_be_reused(client, admin):
    created = await _create_invite(client, admin)
    first = await client.post("/auth/register", json=_registration(created["code"], "first_user"))
    second = await client.post("/auth/register", json=_registration(created["code"], "second_user"))

    assert first.status_code == 201
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_multi_use_invite_allows_each_use(client, admin):
    created = await _create_invite(client, admin, max_uses=2)

    results = [
        (await client.post("/auth/register", json=_registration(created["code"], f"user_{n}"))).status_code
        for n in range(3)
    ]

    assert results == [201, 201, 400]


@pytest.mark.asyncio
async def test_revoked_invite_is_rejected(client, admin):
    created = await _create_invite(client, admin)
    await client.post(f"/admin/invites/{created['id']}/revoke", headers=_headers(admin))

    response = await client.post("/auth/register", json=_registration(created["code"]))

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_expired_invite_is_rejected(client, admin, session):
    created = await _create_invite(client, admin)
    invite = (await session.execute(select(Invite).where(Invite.id == created["id"]))).scalar_one()
    invite.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.flush()

    response = await client.post("/auth/register", json=_registration(created["code"]))

    assert response.status_code == 400
    listed = (await client.get("/admin/invites", headers=_headers(admin))).json()[0]
    assert listed["status"] == "expired"


@pytest.mark.asyncio
async def test_code_is_trimmed(client, admin):
    created = await _create_invite(client, admin)

    response = await client.post("/auth/register", json=_registration(f"  {created['code']}\n"))

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_failed_registration_does_not_burn_the_invite(client, admin, member):
    created = await _create_invite(client, admin)

    clash = await client.post("/auth/register", json=_registration(created["code"], member.username))
    ok = await client.post("/auth/register", json=_registration(created["code"], "fresh_user"))

    assert clash.status_code == 400
    assert clash.json()["detail"] == "Username already registered"
    assert ok.status_code == 201


@pytest.mark.asyncio
async def test_register_ignores_invite_code_when_not_invite_only(client):
    app.dependency_overrides[get_app_settings] = lambda: _settings()

    response = await client.post("/auth/register", json=_registration(None))

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_me_reports_superadmin_flag(client, admin, member):
    admin_me = await client.get("/auth/me", headers=_headers(admin))
    member_me = await client.get("/auth/me", headers=_headers(member))

    assert admin_me.json()["is_superadmin"] is True
    assert member_me.json()["is_superadmin"] is False


@pytest.mark.asyncio
async def test_ensure_superadmin_creates_a_new_user(session):
    user = await ensure_superadmin(session, "root@example.com", "root_user", "secret123")

    assert user.is_superadmin is True
    assert user.hashed_password != "secret123"


@pytest.mark.asyncio
async def test_ensure_superadmin_promotes_an_existing_user(session):
    existing = await _user(session, "promote_me")

    promoted = await ensure_superadmin(session, existing.email, existing.username, None)

    assert promoted.id == existing.id
    assert promoted.is_superadmin is True


@pytest.mark.asyncio
async def test_ensure_superadmin_needs_a_password_for_a_new_user(session):
    with pytest.raises(ValueError):
        await ensure_superadmin(session, "nobody@example.com", "nobody", None)
