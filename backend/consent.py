from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ConsentRecord

NET_WORTH_PURPOSE = "net_worth_processing"
NET_WORTH_NOTICE_VERSION = "1.0"


async def latest_consent(session: AsyncSession, user_id: str, purpose: str) -> ConsentRecord | None:
    result = await session.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == user_id, ConsentRecord.purpose == purpose)
        .order_by(ConsentRecord.created_at.desc(), ConsentRecord.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def has_net_worth_consent(session: AsyncSession, user_id: str) -> bool:
    record = await latest_consent(session, user_id, NET_WORTH_PURPOSE)
    return record is not None and record.granted and record.notice_version == NET_WORTH_NOTICE_VERSION
