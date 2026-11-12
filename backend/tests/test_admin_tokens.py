from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app_config import get_app_settings
from auth_utils import (
    ADMIN_AUDIENCE,
    ADMIN_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_admin_token,
    decode_admin_token,
)


def claims(token: str) -> dict:
    settings = get_app_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm], audience=ADMIN_AUDIENCE)


def test_admin_token_carries_the_admin_audience():
    token = create_admin_token("admin-1", "root_admin")

    assert claims(token)["aud"] == "admin"
    assert claims(token)["sub"] == "admin-1"
    assert decode_admin_token(token) == "admin-1"


def test_admin_token_expires_after_fifteen_minutes():
    token = create_admin_token("admin-1", "root_admin")

    remaining = datetime.fromtimestamp(claims(token)["exp"], timezone.utc) - datetime.now(timezone.utc)

    assert ADMIN_TOKEN_EXPIRE_MINUTES == 15
    assert timedelta(minutes=14) < remaining <= timedelta(minutes=15)


def test_expired_admin_token_is_rejected():
    token = create_access_token(
        {"sub": "admin-1", "username": "root_admin", "aud": ADMIN_AUDIENCE}, timedelta(minutes=-1)
    )

    assert decode_admin_token(token) is None


def test_token_with_a_different_audience_is_rejected():
    token = create_access_token({"sub": "admin-1", "username": "x", "aud": "someone-else"})

    assert decode_admin_token(token) is None


def test_token_without_an_audience_is_rejected_even_with_an_admin_role_claim():
    token = create_access_token({"sub": "admin-1", "username": "x", "role": "admin"})

    assert decode_admin_token(token) is None
