from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from database.repository import (
    AccountRepository,
    BalanceRepository,
    IngestedDocumentRepository,
)
from ingestion.model import NetWorth, Position


def _naive(dt: datetime | None) -> datetime | None:
    """Strip tzinfo so DB-round-tripped datetimes compare cleanly against the
    naive datetimes ingest() itself produces (datetime.fromisoformat() on an
    ISO string with no explicit offset) — a Postgres timestamptz column always
    returns timezone-aware values on read, and pipeline.py's staleness/
    supersession logic compares Position.doc_issued_at values directly, which
    raises TypeError if one side is naive and the other is aware.
    """
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


async def load_current_networth(
    session: AsyncSession, user_id: str, reporting_currency: str
) -> NetWorth:
    balance_repo = BalanceRepository(session)
    balances = await balance_repo.get_latest_balances(user_id=user_id)

    positions: dict[str, Position] = {}
    for balance in balances:
        doc_issued_at = None
        source = None
        if balance.source_document is not None:
            doc_issued_at = _naive(balance.source_document.doc_issued_at)
            source = balance.source_document.source
        position = Position(
            account_name=balance.account.name,
            value=str(balance.amount),
            currency=balance.currency,
            as_of=balance.date,
            units=None,
            nav=None,
            doc_issued_at=doc_issued_at,
            source=source,
        )
        positions[balance.account.name] = position

    as_of = max((p.as_of for p in positions.values()), default=None)
    total = sum(
        (Decimal(p.value) for p in positions.values() if p.currency == reporting_currency),
        start=Decimal("0"),
    )
    return NetWorth(
        as_of=as_of,
        reporting_currency=reporting_currency,
        positions=positions,
        total=str(total),
        warnings=[],
    )


async def persist_networth(
    session: AsyncSession,
    ingestion_run_id: str,
    user_id: str,
    result: NetWorth,
) -> tuple[int, list[str]]:
    account_repo = AccountRepository(session)
    balance_repo = BalanceRepository(session)
    document_repo = IngestedDocumentRepository(session)

    for position in result.positions.values():
        account = await account_repo.get_by_name(user_id, position.account_name)
        if account is None:
            account = await account_repo.create(
                name=position.account_name,
                open_date=position.as_of,
                currency=position.currency,
                user_id=user_id,
            )

        source_document_id = None
        if position.doc_issued_at is not None:
            document = await document_repo.get_or_create(
                ingestion_run_id=ingestion_run_id,
                source=position.source,
                doc_issued_at=_naive(position.doc_issued_at),
            )
            source_document_id = document.id

        await balance_repo.create_or_update(
            account_id=account.id,
            date=position.as_of,
            amount=Decimal(position.value),
            currency=position.currency,
            source_document_id=source_document_id,
        )

    return len(result.positions), result.warnings
