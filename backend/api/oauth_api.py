import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import oauth_providers
from api.auth_api import consume_invite
from app_config import AppSettings, get_app_settings
from auth_utils import create_access_token
from database.models import InviteRedemption, OAuthIdentity, User
from database.session import get_session
from oauth_providers import OAuthError, OAuthProfile

router = APIRouter(prefix="/auth", tags=["oauth"])

STATE_MINUTES = 10
NONCE_COOKIE = "oauth_nonce"
STATE_TYPE = "oauth_state"
MAX_INVITE_LENGTH = 64
USERNAME_MAX = 40


async def get_oauth_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        yield client


def _require_provider(provider: str, settings: AppSettings) -> None:
    if provider not in oauth_providers.PROVIDERS or not oauth_providers.is_enabled(provider, settings):
        raise HTTPException(status_code=404, detail="Unknown or disabled sign-in provider")


def _sign_state(settings: AppSettings, provider: str, nonce: str, invite_code: str) -> str:
    claims = {
        "typ": STATE_TYPE,
        "provider": provider,
        "nonce": nonce,
        "invite": invite_code,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=STATE_MINUTES),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)


def _read_state(settings: AppSettings, state: Optional[str]) -> Optional[dict]:
    if not state:
        return None
    try:
        claims = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
    return claims if claims.get("typ") == STATE_TYPE else None


def _failure(settings: AppSettings, code: str) -> RedirectResponse:
    response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/login/?error={quote(code)}", status_code=302)
    response.delete_cookie(NONCE_COOKIE, path="/")
    return response


def _success(settings: AppSettings, user: User) -> RedirectResponse:
    token = create_access_token(data={"sub": user.id, "username": user.username, "email": user.email})
    response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback/#token={token}", status_code=302)
    response.delete_cookie(NONCE_COOKIE, path="/")
    return response


async def _unique_username(session: AsyncSession, hint: Optional[str]) -> str:
    base = re.sub(r"[^a-z0-9_]+", "", (hint or "").lower())[:USERNAME_MAX]
    if len(base) < 3:
        base = "member"
    candidate = base
    for _ in range(20):
        taken = await session.scalar(select(User.id).where(User.username == candidate))
        if taken is None:
            return candidate
        candidate = f"{base}{secrets.token_hex(2)}"
    return f"{base}{secrets.token_hex(6)}"


@router.get("/providers")
async def list_providers(settings: AppSettings = Depends(get_app_settings)) -> dict[str, bool]:
    enabled = {name: oauth_providers.is_enabled(name, settings) for name in oauth_providers.PROVIDERS}
    return {"password": settings.password_auth_enabled, **enabled}


@router.get("/{provider}/login")
async def start_login(
    provider: str,
    invite_code: str = Query(default="", max_length=MAX_INVITE_LENGTH),
    settings: AppSettings = Depends(get_app_settings),
):
    _require_provider(provider, settings)
    nonce = secrets.token_urlsafe(24)
    state = _sign_state(settings, provider, nonce, invite_code.strip())
    response = RedirectResponse(oauth_providers.authorize_url(provider, settings, state), status_code=302)
    response.set_cookie(
        NONCE_COOKIE,
        nonce,
        max_age=STATE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=settings.oauth_redirect_base_url.startswith("https://"),
        path="/",
    )
    return response


async def _resolve_user(
    session: AsyncSession, settings: AppSettings, profile: OAuthProfile, invite_code: str
) -> User | str:
    identity = await session.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == profile.provider, OAuthIdentity.provider_user_id == profile.subject
        )
    )
    if identity is not None:
        return await session.get(User, identity.user_id)

    trusted_email = profile.email if profile.email and profile.email_verified else None
    if profile.email:
        existing = await session.scalar(select(User).where(User.email == profile.email))
        if existing is not None:
            if trusted_email is None:
                return "email_unverified"
            session.add(OAuthIdentity(user_id=existing.id, provider=profile.provider, provider_user_id=profile.subject))
            await session.commit()
            return existing

    invite_id = None
    if settings.invite_only:
        try:
            invite_id = await consume_invite(session, invite_code)
        except HTTPException:
            return "invite_required"

    user = User(
        email=trusted_email,
        username=await _unique_username(session, profile.username_hint),
        hashed_password=None,
        full_name=profile.name,
        primary_currency="USD",
    )
    session.add(user)
    await session.flush()
    session.add(OAuthIdentity(user_id=user.id, provider=profile.provider, provider_user_id=profile.subject))
    if invite_id is not None:
        session.add(InviteRedemption(invite_id=invite_id, user_id=user.id))
    await session.commit()
    return user


@router.get("/{provider}/callback")
async def finish_login(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    settings: AppSettings = Depends(get_app_settings),
    http_client: httpx.AsyncClient = Depends(get_oauth_http_client),
):
    _require_provider(provider, settings)
    claims = _read_state(settings, state)
    cookie_nonce = request.cookies.get(NONCE_COOKIE)
    if (
        claims is None
        or claims.get("provider") != provider
        or not cookie_nonce
        or not secrets.compare_digest(str(claims.get("nonce", "")), cookie_nonce)
    ):
        return _failure(settings, "state_invalid")
    if error or not code:
        return _failure(settings, "provider_denied")
    try:
        profile = await oauth_providers.fetch_profile(provider, settings, code, http_client)
    except OAuthError:
        return _failure(settings, "provider_failed")
    try:
        outcome = await _resolve_user(session, settings, profile, str(claims.get("invite", "")))
    except IntegrityError:
        await session.rollback()
        return _failure(settings, "provider_failed")
    if isinstance(outcome, str):
        return _failure(settings, outcome)
    return _success(settings, outcome)
