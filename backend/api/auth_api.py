from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app_config import AppSettings, get_app_settings
from auth_utils import decode_token
from database.models import Invite, User
from database.session import get_session

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


class RegistrationInfo(BaseModel):
    invite_required: bool


class UserResponse(BaseModel):
    id: str
    email: Optional[EmailStr] = None
    username: str
    full_name: Optional[str] = None
    location: Optional[str] = None
    primary_currency: str = "USD"

    class Config:
        from_attributes = True


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    token = credentials.credentials
    token_data = decode_token(token)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def consume_invite(session: AsyncSession, code: Optional[str]) -> str:
    code = (code or "").strip()
    invite_id = None
    if code:
        result = await session.execute(
            update(Invite)
            .where(
                Invite.code == code,
                Invite.revoked_at.is_(None),
                Invite.use_count < Invite.max_uses,
                or_(Invite.expires_at.is_(None), Invite.expires_at > func.now()),
            )
            .values(use_count=Invite.use_count + 1)
            .returning(Invite.id)
        )
        invite_id = result.scalar_one_or_none()
    if invite_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired invite code")
    return invite_id


@router.get("/registration", response_model=RegistrationInfo)
async def get_registration_info(settings: AppSettings = Depends(get_app_settings)):
    return RegistrationInfo(invite_required=settings.invite_only)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        location=current_user.location,
        primary_currency=current_user.primary_currency,
    )
