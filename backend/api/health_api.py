from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from build_info import get_build_info
from database.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", **get_build_info()}


@router.get("/health/ready")
async def health_ready(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok", **get_build_info()}
