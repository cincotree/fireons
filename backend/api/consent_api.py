from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_api import get_current_user
from consent import (
    NET_WORTH_NOTICE_VERSION,
    NET_WORTH_PURPOSE,
    has_net_worth_consent,
    latest_consent,
)
from database.models import Account, ConsentRecord, IngestionRun, User
from database.session import get_session

router = APIRouter(prefix="/consent", tags=["consent"])


class ConsentStatus(BaseModel):
    purpose: str
    notice_version: str
    granted: bool
    accepted_version: Optional[str] = None
    updated_at: Optional[datetime] = None


class ConsentGrant(BaseModel):
    notice_version: str
    age_confirmed: bool
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)


class ConsentWithdrawal(ConsentStatus):
    accounts_deleted: int
    runs_deleted: int


async def require_net_worth_consent(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not await has_net_worth_consent(session, current_user.id):
        raise HTTPException(status_code=403, detail="consent_required")
    return current_user


async def _status(session: AsyncSession, user_id: str) -> ConsentStatus:
    record = await latest_consent(session, user_id, NET_WORTH_PURPOSE)
    return ConsentStatus(
        purpose=NET_WORTH_PURPOSE,
        notice_version=NET_WORTH_NOTICE_VERSION,
        granted=await has_net_worth_consent(session, user_id),
        accepted_version=record.notice_version if record and record.granted else None,
        updated_at=record.created_at if record else None,
    )


@router.get("/net-worth", response_model=ConsentStatus)
async def get_net_worth_consent(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _status(session, current_user.id)


@router.post("/net-worth", response_model=ConsentStatus)
async def grant_net_worth_consent(
    body: ConsentGrant,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not body.age_confirmed:
        raise HTTPException(status_code=400, detail="age_confirmation_required")
    if body.notice_version != NET_WORTH_NOTICE_VERSION:
        raise HTTPException(status_code=409, detail="notice_changed")
    session.add(
        ConsentRecord(
            user_id=current_user.id,
            purpose=NET_WORTH_PURPOSE,
            notice_version=body.notice_version,
            granted=True,
            country=body.country.upper() if body.country else None,
            created_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()
    return await _status(session, current_user.id)


@router.delete("/net-worth", response_model=ConsentWithdrawal)
async def withdraw_net_worth_consent(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    accounts = await session.execute(
        delete(Account).where(Account.user_id == current_user.id).returning(Account.id)
    )
    runs = await session.execute(
        delete(IngestionRun).where(IngestionRun.user_id == current_user.id).returning(IngestionRun.id)
    )
    previous = await latest_consent(session, current_user.id, NET_WORTH_PURPOSE)
    session.add(
        ConsentRecord(
            user_id=current_user.id,
            purpose=NET_WORTH_PURPOSE,
            notice_version=NET_WORTH_NOTICE_VERSION,
            granted=False,
            country=previous.country if previous else None,
            created_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()
    status = await _status(session, current_user.id)
    return ConsentWithdrawal(
        **status.model_dump(),
        accounts_deleted=len(accounts.fetchall()),
        runs_deleted=len(runs.fetchall()),
    )
