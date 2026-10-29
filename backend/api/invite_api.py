import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_api import get_current_superadmin, hash_invite_code
from database.models import Invite, InviteRedemption, User
from database.session import get_session

router = APIRouter(prefix="/admin/invites", tags=["invites"])


class InviteCreate(BaseModel):
    label: Optional[str] = Field(default=None, max_length=255)
    max_uses: int = Field(default=1, ge=1, le=1000)
    expires_in_days: Optional[int] = Field(default=14, ge=1, le=365)


class InviteResponse(BaseModel):
    id: str
    label: Optional[str]
    max_uses: int
    use_count: int
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime
    status: str
    redeemed_by: list[str]


class InviteCreatedResponse(InviteResponse):
    code: str


def invite_status(invite: Invite) -> str:
    now = datetime.now(timezone.utc)
    if invite.revoked_at is not None:
        return "revoked"
    if invite.expires_at is not None and invite.expires_at <= now:
        return "expired"
    if invite.use_count >= invite.max_uses:
        return "exhausted"
    return "active"


def to_response(invite: Invite, redeemed_by: list[str]) -> dict:
    return {
        "id": invite.id,
        "label": invite.label,
        "max_uses": invite.max_uses,
        "use_count": invite.use_count,
        "expires_at": invite.expires_at,
        "revoked_at": invite.revoked_at,
        "created_at": invite.created_at,
        "status": invite_status(invite),
        "redeemed_by": redeemed_by,
    }


@router.post("", response_model=InviteCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    data: InviteCreate,
    admin: User = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    code = secrets.token_urlsafe(12)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
        if data.expires_in_days is not None
        else None
    )
    invite = Invite(
        code_hash=hash_invite_code(code),
        label=data.label.strip() if data.label else None,
        max_uses=data.max_uses,
        expires_at=expires_at,
        created_by=admin.id,
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)
    return {**to_response(invite, []), "code": code}


@router.get("", response_model=list[InviteResponse])
async def list_invites(
    _: User = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    invites = (await session.execute(select(Invite).order_by(Invite.created_at.desc()))).scalars().all()
    redemptions = (
        await session.execute(
            select(InviteRedemption.invite_id, User.username).join(User, User.id == InviteRedemption.user_id)
        )
    ).all()
    redeemed: dict[str, list[str]] = {}
    for invite_id, username in redemptions:
        redeemed.setdefault(invite_id, []).append(username)
    return [to_response(invite, redeemed.get(invite.id, [])) for invite in invites]


@router.post("/{invite_id}/revoke", response_model=InviteResponse)
async def revoke_invite(
    invite_id: UUID,
    _: User = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_session),
):
    invite = (await session.execute(select(Invite).where(Invite.id == str(invite_id)))).scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    if invite.revoked_at is None:
        invite.revoked_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(invite)
    usernames = (
        await session.execute(
            select(User.username)
            .join(InviteRedemption, InviteRedemption.user_id == User.id)
            .where(InviteRedemption.invite_id == invite.id)
        )
    ).scalars().all()
    return to_response(invite, list(usernames))
