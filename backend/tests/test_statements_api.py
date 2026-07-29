from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from auth_utils import create_access_token
from database.models import User
from database.repository import AccountRepository
from database.session import get_session
from tests.fixtures.generate_hdfc_fixture import FIXTURES_DIR, TEST_PDF_PASSWORD


def _fixture_bytes(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        email="statements-test@example.com",
        username="statements_test_user",
        hashed_password="unused-in-these-tests",
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = create_access_token(
        data={"sub": test_user.id, "username": test_user.username, "email": test_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestParseStatementEndpoint:
    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/statements/parse",
            files={
                "file": (
                    "statement.pdf",
                    _fixture_bytes("hdfc_statement_valid.pdf"),
                    "application/pdf",
                )
            },
            data={"password": TEST_PDF_PASSWORD, "bank": "HDFC"},
        )
        # HTTPBearer returns 403 (not 401) when no Authorization header is
        # present at all; 401 is reserved for an invalid/expired token.
        assert response.status_code == 403

    async def test_happy_path(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/statements/parse",
            headers=auth_headers,
            files={
                "file": (
                    "statement.pdf",
                    _fixture_bytes("hdfc_statement_valid.pdf"),
                    "application/pdf",
                )
            },
            data={"password": TEST_PDF_PASSWORD, "bank": "HDFC"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["bank"] == "HDFC"
        assert body["account_number_last4"] == "6789"
        assert body["currency"] == "INR"
        assert Decimal(str(body["closing_balance"])) == Decimal("128456.78")
        assert body["suggested_account_name"] == "Assets:Bank:HDFC:6789"
        assert body["warnings"] == []

    async def test_wrong_password_returns_422(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/statements/parse",
            headers=auth_headers,
            files={
                "file": (
                    "statement.pdf",
                    _fixture_bytes("hdfc_statement_valid.pdf"),
                    "application/pdf",
                )
            },
            data={"password": "wrong-password", "bank": "HDFC"},
        )
        assert response.status_code == 422
        assert "password" in response.json()["detail"].lower()

    async def test_oversized_file_rejected(self, client: AsyncClient, auth_headers: dict):
        oversized_content = b"%PDF-1.4\n" + (b"0" * (15 * 1024 * 1024 + 1))
        response = await client.post(
            "/api/statements/parse",
            headers=auth_headers,
            files={"file": ("statement.pdf", oversized_content, "application/pdf")},
            data={"password": TEST_PDF_PASSWORD, "bank": "HDFC"},
        )
        assert response.status_code == 413

    async def test_unsupported_bank_rejected(self, client: AsyncClient, auth_headers: dict):
        response = await client.post(
            "/api/statements/parse",
            headers=auth_headers,
            files={
                "file": (
                    "statement.pdf",
                    _fixture_bytes("hdfc_statement_valid.pdf"),
                    "application/pdf",
                )
            },
            data={"password": TEST_PDF_PASSWORD, "bank": "SBI"},
        )
        assert response.status_code == 400

    async def test_parse_does_not_persist_anything(
        self, client: AsyncClient, auth_headers: dict, session: AsyncSession
    ):
        account_repo = AccountRepository(session)
        assert await account_repo.list_all() == []

        response = await client.post(
            "/api/statements/parse",
            headers=auth_headers,
            files={
                "file": (
                    "statement.pdf",
                    _fixture_bytes("hdfc_statement_valid.pdf"),
                    "application/pdf",
                )
            },
            data={"password": TEST_PDF_PASSWORD, "bank": "HDFC"},
        )
        assert response.status_code == 200
        assert await account_repo.list_all() == []


@pytest.mark.asyncio
class TestConfirmStatementEndpoint:
    async def test_creates_account_and_balance(
        self, client: AsyncClient, auth_headers: dict, test_user: User, session: AsyncSession
    ):
        response = await client.post(
            "/api/statements/confirm",
            headers=auth_headers,
            json={
                "bank": "HDFC",
                "account_name": "Assets:Bank:HDFC:6789",
                "currency": "INR",
                "closing_balance": "123456.78",
                "statement_date": "2025-03-31",
                "account_number": "50100123456789",
                "account_holder_name": "TEST USER",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["account_name"] == "Assets:Bank:HDFC:6789"
        assert Decimal(body["amount"]) == Decimal("123456.78")
        assert body["currency"] == "INR"
        assert body["date"] == "2025-03-31"

        account_repo = AccountRepository(session)
        [account] = await account_repo.list_all(user_id=test_user.id)
        assert account.name == "Assets:Bank:HDFC:6789"
        assert account.meta["account_number"] == "50100123456789"
        assert account.meta["source"] == "statement_upload"

    async def test_rejects_invalid_account_type_prefix(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/statements/confirm",
            headers=auth_headers,
            json={
                "bank": "HDFC",
                "account_name": "NotAValidPrefix:HDFC:6789",
                "currency": "INR",
                "closing_balance": "100.00",
                "statement_date": "2025-03-31",
            },
        )
        assert response.status_code == 400

    async def test_reimporting_same_statement_updates_instead_of_duplicating(
        self, client: AsyncClient, auth_headers: dict, test_user: User, session: AsyncSession
    ):
        payload = {
            "bank": "HDFC",
            "account_name": "Assets:Bank:HDFC:6789",
            "currency": "INR",
            "closing_balance": "123456.78",
            "statement_date": "2025-03-31",
            "account_number": "50100123456789",
            "account_holder_name": "TEST USER",
        }

        first = await client.post(
            "/api/statements/confirm", headers=auth_headers, json=payload
        )
        assert first.status_code == 200

        # Re-importing the same statement (same suggested account name) must
        # update the existing account's balance, not raise a duplicate-key
        # IntegrityError from the DB's unique (user_id, name) constraint.
        second = await client.post(
            "/api/statements/confirm",
            headers=auth_headers,
            json={**payload, "closing_balance": "150000.00", "statement_date": "2025-04-30"},
        )
        assert second.status_code == 200
        assert Decimal(second.json()["amount"]) == Decimal("150000.00")
        assert second.json()["account_id"] == first.json()["account_id"]

        account_repo = AccountRepository(session)
        accounts = await account_repo.list_all(user_id=test_user.id)
        assert len(accounts) == 1
