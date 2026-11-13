from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app_config import AppSettings

GOOGLE = "google"
REDDIT = "reddit"
PROVIDERS = (GOOGLE, REDDIT)
REDDIT_USER_AGENT = "web:fireons:1.0 (by /u/fireons)"


class OAuthError(RuntimeError):
    pass


@dataclass
class OAuthProfile:
    provider: str
    subject: str
    email: str | None
    email_verified: bool
    name: str | None
    username_hint: str | None


def credentials(provider: str, settings: AppSettings) -> tuple[str, str]:
    if provider == GOOGLE:
        return settings.google_oauth_client_id, settings.google_oauth_client_secret
    if provider == REDDIT:
        return settings.reddit_oauth_client_id, settings.reddit_oauth_client_secret
    return "", ""


def is_enabled(provider: str, settings: AppSettings) -> bool:
    client_id, client_secret = credentials(provider, settings)
    return bool(client_id and client_secret)


def redirect_uri(provider: str, settings: AppSettings) -> str:
    return f"{settings.oauth_redirect_base_url.rstrip('/')}/auth/{provider}/callback"


def authorize_url(provider: str, settings: AppSettings, state: str) -> str:
    client_id, _ = credentials(provider, settings)
    if provider == GOOGLE:
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri(provider, settings),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(query)}"
    query = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(provider, settings),
        "response_type": "code",
        "scope": "identity",
        "state": state,
        "duration": "temporary",
    }
    return f"https://www.reddit.com/api/v1/authorize?{urlencode(query)}"


async def _json(response: httpx.Response, what: str) -> dict:
    if response.status_code >= 400:
        raise OAuthError(f"{what} returned {response.status_code}")
    try:
        data = response.json()
    except ValueError:
        raise OAuthError(f"{what} returned invalid JSON") from None
    if not isinstance(data, dict):
        raise OAuthError(f"{what} returned an unexpected body")
    return data


async def fetch_profile(provider: str, settings: AppSettings, code: str, client: httpx.AsyncClient) -> OAuthProfile:
    client_id, client_secret = credentials(provider, settings)
    try:
        if provider == GOOGLE:
            return await _google_profile(settings, code, client, client_id, client_secret)
        return await _reddit_profile(settings, code, client, client_id, client_secret)
    except httpx.HTTPError as exc:
        raise OAuthError(f"{provider} request failed: {type(exc).__name__}") from None


async def _google_profile(settings, code, client, client_id, client_secret) -> OAuthProfile:
    token = await _json(
        await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri(GOOGLE, settings),
                "grant_type": "authorization_code",
            },
        ),
        "Google token endpoint",
    )
    access_token = token.get("access_token")
    if not access_token:
        raise OAuthError("Google did not return an access token")
    info = await _json(
        await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        ),
        "Google userinfo",
    )
    subject = info.get("sub")
    if not subject:
        raise OAuthError("Google did not return a user id")
    email = info.get("email")
    return OAuthProfile(
        provider=GOOGLE,
        subject=str(subject),
        email=email.lower() if isinstance(email, str) else None,
        email_verified=info.get("email_verified") is True,
        name=info.get("name"),
        username_hint=email.split("@")[0] if isinstance(email, str) else None,
    )


async def _reddit_profile(settings, code, client, client_id, client_secret) -> OAuthProfile:
    token = await _json(
        await client.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, client_secret),
            headers={"User-Agent": REDDIT_USER_AGENT},
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri(REDDIT, settings)},
        ),
        "Reddit token endpoint",
    )
    access_token = token.get("access_token")
    if not access_token:
        raise OAuthError("Reddit did not return an access token")
    info = await _json(
        await client.get(
            "https://oauth.reddit.com/api/v1/me",
            headers={"Authorization": f"Bearer {access_token}", "User-Agent": REDDIT_USER_AGENT},
        ),
        "Reddit identity",
    )
    subject = info.get("id")
    if not subject:
        raise OAuthError("Reddit did not return a user id")
    name = info.get("name")
    return OAuthProfile(
        provider=REDDIT,
        subject=str(subject),
        email=None,
        email_verified=False,
        name=None,
        username_hint=name if isinstance(name, str) else None,
    )
