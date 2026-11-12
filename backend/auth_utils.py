
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app_config import get_app_settings


ADMIN_AUDIENCE = "admin"
ADMIN_TOKEN_EXPIRE_MINUTES = 15


class TokenData(BaseModel):
    user_id: str
    username: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_app_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_admin_token(admin_id: str, username: str) -> str:
    return create_access_token(
        {"sub": admin_id, "username": username, "aud": ADMIN_AUDIENCE},
        timedelta(minutes=ADMIN_TOKEN_EXPIRE_MINUTES),
    )


def decode_admin_token(token: str) -> Optional[str]:
    settings = get_app_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience=ADMIN_AUDIENCE,
            options={"require_aud": True},
        )
    except JWTError:
        return None
    return payload.get("sub")


def decode_token(token: str) -> Optional[TokenData]:
    settings = get_app_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        email: str = payload.get("email")

        if user_id is None or username is None or email is None:
            return None

        return TokenData(user_id=user_id, username=username, email=email)
    except JWTError:
        return None
