from urllib.parse import parse_qs, urlparse

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import oauth_providers
from api.oauth_api import get_oauth_http_client
from app import app
from app_config import AppSettings, get_app_settings
from database.models import Invite, InviteRedemption, OAuthIdentity, User
from database.session import get_session

SECRET = get_app_settings().secret_key
FRONTEND = "http://localhost:3000"


def settings_for(**overrides) -> AppSettings:
    values = dict(
        secret_key=SECRET,
        frontend_url=FRONTEND,
        oauth_redirect_base_url="http://localhost:8000",
        google_oauth_client_id="google-client",
        google_oauth_client_secret="google-secret",
        reddit_oauth_client_id="reddit-client",
        reddit_oauth_client_secret="reddit-secret",
    )
    values.update(overrides)
    return AppSettings(_env_file=None, **values)


class Provider:
    def __init__(self):
        self.google_info = {"sub": "g-1", "email": "Pat@Example.com", "email_verified": True, "name": "Pat Doe"}
        self.reddit_info = {"id": "r-1", "name": "Pat_On_Reddit"}
        self.token_status = 200
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if url.startswith("https://oauth2.googleapis.com/token"):
            return httpx.Response(self.token_status, json={"access_token": "g-access"})
        if url.startswith("https://openidconnect.googleapis.com/v1/userinfo"):
            return httpx.Response(200, json=self.google_info)
        if url.startswith("https://www.reddit.com/api/v1/access_token"):
            return httpx.Response(self.token_status, json={"access_token": "r-access"})
        if url.startswith("https://oauth.reddit.com/api/v1/me"):
            return httpx.Response(200, json=self.reddit_info)
        return httpx.Response(404)


@pytest.fixture
def provider():
    return Provider()


@pytest_asyncio.fixture
async def client(session: AsyncSession, provider: Provider):
    async def override_get_session():
        yield session

    async def override_http_client():
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider.handler)) as http:
            yield http

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_app_settings] = lambda: settings_for()
    app.dependency_overrides[get_oauth_http_client] = override_http_client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def begin(client, name, **params):
    response = await client.get(f"/auth/{name}/login", params=params, follow_redirects=False)
    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    return response, query["state"][0]


async def finish(client, name, state, **params):
    return await client.get(
        f"/auth/{name}/callback", params={"code": "the-code", "state": state, **params}, follow_redirects=False
    )


def landing(response):
    location = response.headers["location"]
    assert location.startswith(f"{FRONTEND}/auth/callback/#token=")
    return jwt.decode(location.split("#token=")[1], SECRET, algorithms=["HS256"])


def failure_code(response):
    location = response.headers["location"]
    assert location.startswith(f"{FRONTEND}/login/?error=")
    return location.split("error=")[1]


@pytest.mark.asyncio
async def test_providers_report_which_sign_ins_are_configured(client):
    assert (await client.get("/auth/providers")).json() == {"google": True, "reddit": True}

    app.dependency_overrides[get_app_settings] = lambda: settings_for(reddit_oauth_client_secret="")
    assert (await client.get("/auth/providers")).json() == {"google": True, "reddit": False}


@pytest.mark.asyncio
async def test_login_redirects_to_google_without_leaking_the_secret(client):
    response, state = await begin(client, "google")

    location = response.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"] == ["google-client"]
    assert query["redirect_uri"] == ["http://localhost:8000/auth/google/callback"]
    assert query["scope"] == ["openid email profile"]
    assert "google-secret" not in location
    assert "oauth_nonce=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert state


@pytest.mark.asyncio
async def test_login_redirects_to_reddit_asking_only_for_identity(client):
    response, _ = await begin(client, "reddit")

    parsed = urlparse(response.headers["location"])
    query = parse_qs(parsed.query)
    assert parsed.netloc == "www.reddit.com"
    assert query["scope"] == ["identity"]
    assert query["duration"] == ["temporary"]
    assert "reddit-secret" not in response.headers["location"]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["facebook", "github", "..%2Fgoogle"])
async def test_unknown_provider_is_not_found(client, name):
    assert (await client.get(f"/auth/{name}/login", follow_redirects=False)).status_code == 404
    assert (await client.get(f"/auth/{name}/callback", follow_redirects=False)).status_code == 404


@pytest.mark.asyncio
async def test_unconfigured_provider_is_not_found(client):
    app.dependency_overrides[get_app_settings] = lambda: settings_for(google_oauth_client_id="")

    assert (await client.get("/auth/google/login", follow_redirects=False)).status_code == 404


@pytest.mark.asyncio
async def test_google_sign_in_creates_a_user_and_returns_a_token(client, session):
    _, state = await begin(client, "google")

    response = await finish(client, "google", state)

    claims = landing(response)
    user = await session.scalar(select(User).where(User.id == claims["sub"]))
    assert user.email == "pat@example.com"
    assert user.full_name == "Pat Doe"
    assert user.username == "pat"
    identity = await session.scalar(select(OAuthIdentity).where(OAuthIdentity.user_id == user.id))
    assert (identity.provider, identity.provider_user_id) == ("google", "g-1")


@pytest.mark.asyncio
async def test_signing_in_again_reuses_the_same_user(client, session):
    _, first_state = await begin(client, "google")
    first = landing(await finish(client, "google", first_state))
    _, second_state = await begin(client, "google")
    second = landing(await finish(client, "google", second_state))

    assert first["sub"] == second["sub"]
    assert await session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.asyncio
async def test_google_links_to_an_existing_account_with_the_same_verified_email(client, session):
    existing = User(email="pat@example.com", username="pat_original")
    session.add(existing)
    await session.flush()
    _, state = await begin(client, "google")

    claims = landing(await finish(client, "google", state))

    assert claims["sub"] == existing.id
    assert await session.scalar(select(func.count()).select_from(User)) == 1
    assert await session.scalar(select(func.count()).select_from(OAuthIdentity)) == 1


@pytest.mark.asyncio
async def test_an_unverified_google_email_never_takes_over_an_account(client, session, provider):
    session.add(User(email="pat@example.com", username="pat_original"))
    await session.flush()
    provider.google_info["email_verified"] = False
    _, state = await begin(client, "google")

    response = await finish(client, "google", state)

    assert failure_code(response) == "email_unverified"
    assert await session.scalar(select(func.count()).select_from(OAuthIdentity)) == 0


@pytest.mark.asyncio
async def test_reddit_sign_in_creates_a_user_without_an_email(client, session):
    _, state = await begin(client, "reddit")

    claims = landing(await finish(client, "reddit", state))

    user = await session.scalar(select(User).where(User.id == claims["sub"]))
    assert user.email is None
    assert user.username == "pat_on_reddit"
    assert claims["email"] is None


@pytest.mark.asyncio
async def test_username_collisions_get_a_suffix(client, session):
    session.add(User(email="other@example.com", username="pat"))
    await session.flush()
    _, state = await begin(client, "google")

    claims = landing(await finish(client, "google", state))

    user = await session.scalar(select(User).where(User.id == claims["sub"]))
    assert user.username != "pat"
    assert user.username.startswith("pat")


@pytest.mark.asyncio
async def test_the_token_works_for_me_even_without_an_email(client):
    _, state = await begin(client, "reddit")
    token = landing_token(await finish(client, "reddit", state))

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me.status_code == 200
    assert me.json()["username"] == "pat_on_reddit"
    assert me.json()["email"] is None


def landing_token(response):
    landing(response)
    return response.headers["location"].split("#token=")[1]


@pytest.mark.asyncio
async def test_callback_without_the_matching_cookie_is_rejected(client, session):
    _, state = await begin(client, "google")
    client.cookies.clear()

    response = await finish(client, "google", state)

    assert failure_code(response) == "state_invalid"
    assert await session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["", "garbage", "a.b.c"])
async def test_callback_with_a_forged_state_is_rejected(client, state):
    await begin(client, "google")

    assert failure_code(await finish(client, "google", state)) == "state_invalid"


@pytest.mark.asyncio
async def test_a_state_issued_for_one_provider_cannot_finish_another(client):
    _, state = await begin(client, "google")

    assert failure_code(await finish(client, "reddit", state)) == "state_invalid"


@pytest.mark.asyncio
async def test_the_user_denying_access_returns_to_login(client):
    _, state = await begin(client, "google")

    response = await client.get(
        "/auth/google/callback", params={"error": "access_denied", "state": state}, follow_redirects=False
    )

    assert failure_code(response) == "provider_denied"


@pytest.mark.asyncio
async def test_a_failing_provider_returns_to_login_without_leaking_details(client, provider):
    provider.token_status = 500
    _, state = await begin(client, "google")

    response = await finish(client, "google", state)

    assert failure_code(response) == "provider_failed"
    assert "google-secret" not in response.headers["location"]


@pytest.mark.asyncio
async def test_invite_only_blocks_new_social_sign_ups_without_a_code(client, session):
    app.dependency_overrides[get_app_settings] = lambda: settings_for(invite_only=True)
    _, state = await begin(client, "google")

    response = await finish(client, "google", state)

    assert failure_code(response) == "invite_required"
    assert await session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.asyncio
async def test_invite_only_accepts_a_valid_code_once(client, session):
    app.dependency_overrides[get_app_settings] = lambda: settings_for(invite_only=True)
    session.add(Invite(code="welcome", max_uses=1))
    await session.flush()
    _, state = await begin(client, "google", invite_code="welcome")

    landing(await finish(client, "google", state))

    invite = await session.scalar(select(Invite).where(Invite.code == "welcome"))
    assert invite.use_count == 1


@pytest.mark.asyncio
async def test_invite_only_lets_existing_social_users_sign_in_without_a_code(client, session):
    _, first_state = await begin(client, "google")
    landing(await finish(client, "google", first_state))
    app.dependency_overrides[get_app_settings] = lambda: settings_for(invite_only=True)
    _, state = await begin(client, "google")

    landing(await finish(client, "google", state))


def test_provider_helpers_build_the_expected_redirect_uri():
    settings = settings_for(oauth_redirect_base_url="https://api.example.com/")

    assert oauth_providers.redirect_uri("google", settings) == "https://api.example.com/auth/google/callback"


async def sign_up(client, provider, subject, code=None):
    provider.google_info = {"sub": subject, "email": f"{subject}@example.com", "email_verified": True, "name": subject}
    params = {"invite_code": code} if code is not None else {}
    _, state = await begin(client, "google", **params)
    return await finish(client, "google", state)


async def add_invite(session, code="welcome-code", **fields):
    invite = Invite(code=code, max_uses=fields.pop("max_uses", 1), **fields)
    session.add(invite)
    await session.flush()
    return invite


@pytest.fixture
def invite_only(client):
    app.dependency_overrides[get_app_settings] = lambda: settings_for(invite_only=True)


@pytest.mark.asyncio
async def test_registration_info_reports_invite_requirement(client):
    assert (await client.get("/auth/registration")).json() == {"invite_required": False}

    app.dependency_overrides[get_app_settings] = lambda: settings_for(invite_only=True)
    assert (await client.get("/auth/registration")).json() == {"invite_required": True}


@pytest.mark.asyncio
async def test_a_valid_invite_records_the_redemption(client, session, provider, invite_only):
    invite = await add_invite(session)

    claims = landing(await sign_up(client, provider, "ann", "welcome-code"))

    await session.refresh(invite)
    assert invite.use_count == 1
    redemption = (await session.execute(select(InviteRedemption))).scalar_one()
    assert (redemption.invite_id, redemption.user_id) == (invite.id, claims["sub"])


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [None, "", "   ", "not-the-code"])
async def test_missing_or_unknown_codes_are_rejected(client, session, provider, invite_only, code):
    await add_invite(session)

    response = await sign_up(client, provider, "bob", code)

    assert failure_code(response) == "invite_required"


@pytest.mark.asyncio
async def test_a_single_use_invite_cannot_be_reused(client, session, provider, invite_only):
    await add_invite(session)

    first = await sign_up(client, provider, "first", "welcome-code")
    second = await sign_up(client, provider, "second", "welcome-code")

    landing(first)
    assert failure_code(second) == "invite_required"


@pytest.mark.asyncio
async def test_a_multi_use_invite_allows_each_use(client, session, provider, invite_only):
    await add_invite(session, max_uses=2)

    results = [await sign_up(client, provider, f"user{n}", "welcome-code") for n in range(3)]

    landing(results[0])
    landing(results[1])
    assert failure_code(results[2]) == "invite_required"


@pytest.mark.asyncio
async def test_revoked_and_expired_invites_are_rejected(client, session, provider, invite_only):
    await add_invite(session, "revoked", revoked_at=datetime.now(timezone.utc))
    await add_invite(session, "expired", expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))

    assert failure_code(await sign_up(client, provider, "a", "revoked")) == "invite_required"
    assert failure_code(await sign_up(client, provider, "b", "expired")) == "invite_required"


@pytest.mark.asyncio
async def test_an_invite_with_a_future_expiry_is_accepted(client, session, provider, invite_only):
    await add_invite(session, expires_at=datetime.now(timezone.utc) + timedelta(days=1))

    landing(await sign_up(client, provider, "carl", "welcome-code"))


@pytest.mark.asyncio
async def test_the_invite_code_is_trimmed(client, session, provider, invite_only):
    await add_invite(session)

    landing(await sign_up(client, provider, "dana", "  welcome-code  "))


@pytest.mark.asyncio
async def test_a_failed_provider_exchange_does_not_burn_the_invite(client, session, provider, invite_only):
    invite = await add_invite(session)
    provider.token_status = 500

    response = await sign_up(client, provider, "erin", "welcome-code")

    assert failure_code(response) == "provider_failed"
    await session.refresh(invite)
    assert invite.use_count == 0


@pytest.mark.asyncio
async def test_the_invite_code_is_ignored_when_not_invite_only(client, session, provider):
    invite = await add_invite(session)

    landing(await sign_up(client, provider, "fay", "welcome-code"))

    await session.refresh(invite)
    assert invite.use_count == 0
