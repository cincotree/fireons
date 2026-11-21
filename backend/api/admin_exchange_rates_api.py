from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_api import require_admin
from database.models import Admin
from database.repository import ExchangeRateRepository
from database.session import get_session

router = APIRouter(prefix="/admin/exchange-rates", tags=["admin-exchange-rates"])


class ExchangeRateResponse(BaseModel):
    id: str
    date: date
    from_currency: str
    to_currency: str
    rate: Decimal
    source: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[ExchangeRateResponse])
async def list_exchange_rates(
    from_currency: Optional[str] = Query(None, min_length=1, max_length=10),
    to_currency: Optional[str] = Query(None, min_length=1, max_length=10),
    limit: int = Query(100, ge=1, le=500),
    _: Admin = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await ExchangeRateRepository(session).list_all(
        from_currency.upper() if from_currency else None,
        to_currency.upper() if to_currency else None,
        limit,
    )
