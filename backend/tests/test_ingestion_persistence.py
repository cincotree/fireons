from datetime import date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.repository import (
    AccountRepository,
    BalanceRepository,
    IngestedDocumentRepository,
    IngestionRunRepository,
)
from ingestion.model import NetWorth, Position
from ingestion.persistence import load_current_networth, persist_networth


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        email="ingestion-persistence-test@example.com",
        username="ingestion_persistence_test_user",
        hashed_password="unused-in-these-tests",
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
class TestAccountGetByName:
    async def test_finds_existing_account(self, session: AsyncSession, test_user: User):
        account_repo = AccountRepository(session)
        created = await account_repo.create(
            name="Assets:Bank:HDFC:1234",
            open_date=date(2026, 1, 1),
            currency="INR",
            user_id=test_user.id,
        )

        found = await account_repo.get_by_name(test_user.id, "Assets:Bank:HDFC:1234")

        assert found is not None
        assert found.id == created.id

    async def test_returns_none_for_missing_account(
        self, session: AsyncSession, test_user: User
    ):
        account_repo = AccountRepository(session)
        found = await account_repo.get_by_name(test_user.id, "Assets:Bank:DoesNotExist:0000")
        assert found is None


@pytest.mark.asyncio
class TestIngestedDocumentRepository:
    async def test_get_or_create_dedups_identical_key(
        self, session: AsyncSession, test_user: User
    ):
        run = await IngestionRunRepository(session).create(user_id=test_user.id, file_count=1)
        doc_repo = IngestedDocumentRepository(session)

        first = await doc_repo.get_or_create(
            ingestion_run_id=run.id, source="CAMS", doc_issued_at=datetime(2026, 8, 2)
        )
        second = await doc_repo.get_or_create(
            ingestion_run_id=run.id, source="CAMS", doc_issued_at=datetime(2026, 8, 2)
        )

        assert first.id == second.id

    async def test_different_source_creates_distinct_document(
        self, session: AsyncSession, test_user: User
    ):
        run = await IngestionRunRepository(session).create(user_id=test_user.id, file_count=1)
        doc_repo = IngestedDocumentRepository(session)

        cams_doc = await doc_repo.get_or_create(
            ingestion_run_id=run.id, source="CAMS", doc_issued_at=datetime(2026, 8, 2)
        )
        cdsl_doc = await doc_repo.get_or_create(
            ingestion_run_id=run.id, source="CDSL", doc_issued_at=datetime(2026, 8, 2)
        )

        assert cams_doc.id != cdsl_doc.id


@pytest.mark.asyncio
class TestIngestionRunLifecycle:
    async def test_create_mark_processing_mark_succeeded(
        self, session: AsyncSession, test_user: User
    ):
        run_repo = IngestionRunRepository(session)
        run = await run_repo.create(user_id=test_user.id, file_count=3)
        assert run.status.value == "pending"

        await run_repo.mark_processing(run.id)
        fetched = await run_repo.get_by_id(run.id, test_user.id)
        assert fetched.status.value == "processing"

        await run_repo.mark_succeeded(run.id, positions_count=5, warnings=["a warning"])
        fetched = await run_repo.get_by_id(run.id, test_user.id)
        assert fetched.status.value == "succeeded"
        assert fetched.positions_count == 5
        assert fetched.warnings == ["a warning"]
        assert fetched.completed_at is not None

    async def test_mark_failed(self, session: AsyncSession, test_user: User):
        run_repo = IngestionRunRepository(session)
        run = await run_repo.create(user_id=test_user.id, file_count=1)

        await run_repo.mark_failed(run.id, "boom")
        fetched = await run_repo.get_by_id(run.id, test_user.id)

        assert fetched.status.value == "failed"
        assert fetched.error_message == "boom"
        assert fetched.completed_at is not None

    async def test_get_by_id_scoped_to_owner(self, session: AsyncSession, test_user: User):
        other_user = User(
            email="other-user@example.com",
            username="other_user",
            hashed_password="unused",
        )
        session.add(other_user)
        await session.flush()

        run_repo = IngestionRunRepository(session)
        run = await run_repo.create(user_id=test_user.id, file_count=1)

        assert await run_repo.get_by_id(run.id, other_user.id) is None
        assert await run_repo.get_by_id(run.id, test_user.id) is not None


@pytest.mark.asyncio
class TestPersistAndLoadNetWorth:
    async def test_persist_creates_accounts_and_balances(
        self, session: AsyncSession, test_user: User
    ):
        run = await IngestionRunRepository(session).create(user_id=test_user.id, file_count=1)
        result = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={
                "Assets:Bank:HDFC:6789": Position(
                    account_name="Assets:Bank:HDFC:6789",
                    value="150000.00",
                    currency="INR",
                    as_of=date(2026, 7, 31),
                    doc_issued_at=datetime(2026, 7, 31),
                    source="HDFC",
                ),
                "Assets:Investment:SGB:SGB2028SeriesIV": Position(
                    account_name="Assets:Investment:SGB:SGB2028SeriesIV",
                    value="62000.00",
                    currency="INR",
                    as_of=date(2026, 7, 6),
                    units="10",
                    doc_issued_at=None,
                    source=None,
                ),
            },
            total="212000.00",
            warnings=["a soft warning"],
        )

        positions_count, warnings = await persist_networth(session, run.id, test_user.id, result)

        assert positions_count == 2
        assert warnings == ["a soft warning"]

        account_repo = AccountRepository(session)
        hdfc_account = await account_repo.get_by_name(test_user.id, "Assets:Bank:HDFC:6789")
        assert hdfc_account is not None
        assert hdfc_account.account_type.value == "Assets"
        assert hdfc_account.currency == "INR"

        balances = await BalanceRepository(session).get_latest_balances(user_id=test_user.id)
        by_name = {b.account.name: b for b in balances}

        hdfc_balance = by_name["Assets:Bank:HDFC:6789"]
        assert hdfc_balance.amount == 150000
        assert hdfc_balance.source_document is not None
        assert hdfc_balance.source_document.source == "HDFC"

        sgb_balance = by_name["Assets:Investment:SGB:SGB2028SeriesIV"]
        assert sgb_balance.amount == 62000
        assert sgb_balance.source_document_id is None

    async def test_persist_is_idempotent_on_second_run(
        self, session: AsyncSession, test_user: User
    ):
        run1 = await IngestionRunRepository(session).create(user_id=test_user.id, file_count=1)
        position = Position(
            account_name="Assets:Bank:HDFC:6789",
            value="150000.00",
            currency="INR",
            as_of=date(2026, 7, 31),
            doc_issued_at=datetime(2026, 7, 31),
            source="HDFC",
        )
        first_result = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={"Assets:Bank:HDFC:6789": position},
            total="150000.00",
        )
        await persist_networth(session, run1.id, test_user.id, first_result)

        run2 = await IngestionRunRepository(session).create(user_id=test_user.id, file_count=1)
        updated_position = position.model_copy(update={"value": "160000.00"})
        second_result = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={"Assets:Bank:HDFC:6789": updated_position},
            total="160000.00",
        )
        await persist_networth(session, run2.id, test_user.id, second_result)

        balances = await BalanceRepository(session).get_latest_balances(user_id=test_user.id)
        assert len(balances) == 1
        assert balances[0].amount == 160000

    async def test_load_current_networth_empty_for_new_user(
        self, session: AsyncSession, test_user: User
    ):
        current = await load_current_networth(session, test_user.id, "INR")
        assert current.positions == {}
        assert current.total == "0"

    async def test_load_current_networth_round_trips_doc_issued_at_and_source(
        self, session: AsyncSession, test_user: User
    ):
        run = await IngestionRunRepository(session).create(user_id=test_user.id, file_count=1)
        result = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={
                "Assets:Investment:MutualFund:SampleAMC1:FOLIO001:SchemeAlpha": Position(
                    account_name="Assets:Investment:MutualFund:SampleAMC1:FOLIO001:SchemeAlpha",
                    value="5000.00",
                    currency="INR",
                    as_of=date(2026, 7, 31),
                    doc_issued_at=datetime(2026, 8, 2),
                    source="CAMS",
                )
            },
            total="5000.00",
        )
        await persist_networth(session, run.id, test_user.id, result)

        current = await load_current_networth(session, test_user.id, "INR")

        loaded = current.positions["Assets:Investment:MutualFund:SampleAMC1:FOLIO001:SchemeAlpha"]
        # Balance.amount is Numeric(20, 4), so it round-trips as "5000.0000" —
        # numerically identical, just more decimal places than the original
        # "5000.00"; compare as Decimal rather than exact string, same tolerance
        # the eval harness's canonical() already applies for this exact reason.
        assert Decimal(loaded.value) == Decimal("5000.00")
        assert loaded.source == "CAMS"
        assert loaded.doc_issued_at == datetime(2026, 8, 2)
        assert loaded.doc_issued_at.tzinfo is None
