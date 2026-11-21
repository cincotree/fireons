from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from auth_utils import create_access_token
from consent import NET_WORTH_NOTICE_VERSION, NET_WORTH_PURPOSE
from database.models import Account, ConsentRecord, IngestionRun, User
from database.repository import AccountRepository, BalanceRepository, IngestionRunRepository
from database.session import get_session

URL = "/consent/net-worth"


@pytest_asyncio.fixture
async def member(session: AsyncSession) -> User:
    user = User(email="consent-test@example.com", username="consent_test_user")
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def headers(member: User) -> dict:
    token = create_access_token(data={"sub": member.id, "username": member.username, "email": member.email})
    return {"Authorization": f"Bearer {token}"}


def grant_body(**overrides) -> dict:
    body = {"notice_version": NET_WORTH_NOTICE_VERSION, "age_confirmed": True, "country": "IN"}
    body.update(overrides)
    return body


async def records(session: AsyncSession, user: User) -> list[ConsentRecord]:
    result = await session.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == user.id).order_by(ConsentRecord.created_at)
    )
    return list(result.scalars())


@pytest.mark.asyncio
class TestConsentStatus:
    async def test_requires_authentication(self, client: AsyncClient):
        assert (await client.get(URL)).status_code in (401, 403)
        assert (await client.post(URL, json=grant_body())).status_code in (401, 403)
        assert (await client.delete(URL)).status_code in (401, 403)

    async def test_new_user_has_not_consented(self, client: AsyncClient, headers: dict):
        response = await client.get(URL, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["granted"] is False
        assert body["purpose"] == NET_WORTH_PURPOSE
        assert body["notice_version"] == NET_WORTH_NOTICE_VERSION
        assert body["accepted_version"] is None


@pytest.mark.asyncio
class TestGrantConsent:
    async def test_grant_is_recorded_with_version_and_country(
        self, client: AsyncClient, headers: dict, session: AsyncSession, member: User
    ):
        response = await client.post(URL, json=grant_body(country="us"), headers=headers)

        assert response.status_code == 200
        assert response.json()["granted"] is True
        assert response.json()["accepted_version"] == NET_WORTH_NOTICE_VERSION
        stored = await records(session, member)
        assert [(r.purpose, r.granted, r.notice_version, r.country) for r in stored] == [
            (NET_WORTH_PURPOSE, True, NET_WORTH_NOTICE_VERSION, "US")
        ]
        assert (await client.get(URL, headers=headers)).json()["granted"] is True

    async def test_age_must_be_confirmed(
        self, client: AsyncClient, headers: dict, session: AsyncSession, member: User
    ):
        response = await client.post(URL, json=grant_body(age_confirmed=False), headers=headers)

        assert response.status_code == 400
        assert response.json()["detail"] == "age_confirmation_required"
        assert await records(session, member) == []

    async def test_stale_notice_version_is_refused(
        self, client: AsyncClient, headers: dict, session: AsyncSession, member: User
    ):
        response = await client.post(URL, json=grant_body(notice_version="0.1"), headers=headers)

        assert response.status_code == 409
        assert response.json()["detail"] == "notice_changed"
        assert await records(session, member) == []

    @pytest.mark.parametrize("country", ["", "IND", "I"])
    async def test_country_must_be_two_letters(self, client: AsyncClient, headers: dict, country: str):
        response = await client.post(URL, json=grant_body(country=country), headers=headers)

        assert response.status_code == 422

    async def test_country_is_optional(self, client: AsyncClient, headers: dict):
        body = {"notice_version": NET_WORTH_NOTICE_VERSION, "age_confirmed": True}

        assert (await client.post(URL, json=body, headers=headers)).status_code == 200

    async def test_consent_to_an_older_notice_version_no_longer_counts(
        self, client: AsyncClient, headers: dict, session: AsyncSession, member: User
    ):
        session.add(
            ConsentRecord(user_id=member.id, purpose=NET_WORTH_PURPOSE, notice_version="0.9", granted=True)
        )
        await session.flush()

        body = (await client.get(URL, headers=headers)).json()

        assert body["granted"] is False
        assert body["accepted_version"] == "0.9"


@pytest.mark.asyncio
class TestGate:
    async def test_account_creation_needs_consent(self, client: AsyncClient, headers: dict):
        payload = {"name": "Assets:Bank:Gate", "currency": "USD"}

        blocked = await client.post("/accounts", json=payload, headers=headers)
        await client.post(URL, json=grant_body(), headers=headers)
        allowed = await client.post("/accounts", json=payload, headers=headers)

        assert blocked.status_code == 403
        assert blocked.json()["detail"] == "consent_required"
        assert allowed.status_code == 200

    async def test_balance_entry_needs_consent(
        self, client: AsyncClient, headers: dict, session: AsyncSession, member: User
    ):
        account = await AccountRepository(session).create(
            name="Assets:Bank:Gate", open_date=date(2026, 1, 1), currency="USD", user_id=member.id
        )
        payload = {"amount": "10.00", "currency": "USD", "date": "2026-01-02"}

        blocked = await client.post(f"/accounts/{account.id}/balance", json=payload, headers=headers)
        await client.post(URL, json=grant_body(), headers=headers)
        allowed = await client.post(f"/accounts/{account.id}/balance", json=payload, headers=headers)

        assert blocked.status_code == 403
        assert allowed.status_code == 200

    async def test_statement_upload_and_check_need_consent(self, client: AsyncClient, headers: dict):
        files = {"files": ("statement.pdf", b"%PDF-1.4", "application/pdf")}

        check = await client.post("/ingestion/check", files=files, headers=headers)
        upload = await client.post("/ingestion/upload", files=files, headers=headers)

        assert check.status_code == 403
        assert upload.status_code == 403
        assert check.json()["detail"] == "consent_required"

    async def test_reading_existing_data_is_not_blocked(self, client: AsyncClient, headers: dict):
        assert (await client.get("/accounts", headers=headers)).status_code == 200

    async def test_withdrawn_consent_blocks_again(self, client: AsyncClient, headers: dict):
        await client.post(URL, json=grant_body(), headers=headers)
        await client.delete(URL, headers=headers)

        response = await client.post("/accounts", json={"name": "Assets:Bank:X", "currency": "USD"}, headers=headers)

        assert response.status_code == 403


@pytest.mark.asyncio
class TestWithdrawal:
    async def test_withdrawal_erases_net_worth_data_and_logs_it(
        self, client: AsyncClient, headers: dict, session: AsyncSession, member: User
    ):
        await client.post(URL, json=grant_body(country="GB"), headers=headers)
        account = await AccountRepository(session).create(
            name="Assets:Bank:Erase", open_date=date(2026, 1, 1), currency="USD", user_id=member.id
        )
        await BalanceRepository(session).create_or_update(
            account_id=account.id, date=date(2026, 1, 2), amount=Decimal("5.00"), currency="USD"
        )
        await IngestionRunRepository(session).create(user_id=member.id, file_count=1)
        await session.flush()

        response = await client.delete(URL, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert (body["granted"], body["accounts_deleted"], body["runs_deleted"]) == (False, 1, 1)
        assert (await session.scalars(select(Account).where(Account.user_id == member.id))).all() == []
        assert (await session.scalars(select(IngestionRun).where(IngestionRun.user_id == member.id))).all() == []
        assert [(r.granted, r.country) for r in await records(session, member)] == [(True, "GB"), (False, "GB")]

    async def test_withdrawal_only_touches_the_callers_data(
        self, client: AsyncClient, headers: dict, session: AsyncSession
    ):
        other = User(email="other-consent@example.com", username="other_consent_user")
        session.add(other)
        await session.flush()
        await AccountRepository(session).create(
            name="Assets:Bank:Other", open_date=date(2026, 1, 1), currency="USD", user_id=other.id
        )

        await client.delete(URL, headers=headers)

        remaining = (await session.scalars(select(Account).where(Account.user_id == other.id))).all()
        assert len(remaining) == 1

    async def test_withdrawing_without_prior_consent_is_harmless(self, client: AsyncClient, headers: dict):
        response = await client.delete(URL, headers=headers)

        assert response.status_code == 200
        assert response.json()["granted"] is False
        assert response.json()["accounts_deleted"] == 0

    async def test_user_can_consent_again_after_withdrawing(self, client: AsyncClient, headers: dict):
        await client.post(URL, json=grant_body(), headers=headers)
        await client.delete(URL, headers=headers)
        await client.post(URL, json=grant_body(), headers=headers)

        assert (await client.get(URL, headers=headers)).json()["granted"] is True
