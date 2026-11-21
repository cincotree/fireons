from io import BytesIO

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from auth_utils import create_access_token
from database.models import User
from database.session import get_session


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        email="ingestion-check-test@example.com",
        username="ingestion_check_test_user",
        hashed_password="unused-in-these-tests",
    )
    session.add(user)
    await session.flush()
    return user


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
async def auth_headers(test_user: User) -> dict:
    token = create_access_token(
        data={"sub": test_user.id, "username": test_user.username, "email": test_user.email}
    )
    return {"Authorization": f"Bearer {token}"}


def _render_pdf_bytes(text: str) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(72, 720, text)
    c.save()
    return buffer.getvalue()


def _encrypted_pdf_bytes(text: str, user_password: str, owner_password: str) -> bytes:
    reader = PdfReader(BytesIO(_render_pdf_bytes(text)))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=user_password, owner_password=owner_password)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.mark.asyncio
class TestIngestionCheck:
    async def test_unencrypted_file_needs_no_password(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/ingestion/check",
            headers=auth_headers,
            files={"files": ("plain.pdf", _render_pdf_bytes("plain statement"), "application/pdf")},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["files"] == [{"filename": "plain.pdf", "needs_password": False}]

    async def test_real_password_protected_file_needs_password(
        self, client: AsyncClient, auth_headers: dict
    ):
        pdf_bytes = _encrypted_pdf_bytes(
            "protected statement", user_password="Secret123", owner_password="OwnerSecret456"
        )
        response = await client.post(
            "/api/ingestion/check",
            headers=auth_headers,
            files={"files": ("protected.pdf", pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["files"] == [{"filename": "protected.pdf", "needs_password": True}]

    async def test_owner_password_only_file_does_not_need_a_password(
        self, client: AsyncClient, auth_headers: dict
    ):
        """A statement encrypted with an empty user password (owner-password-only
        protection, restricting printing/editing but not requiring a password to
        open) must be reported as not needing a password — this is the real-world
        shape of many bank statement PDFs, and is what a plain is_encrypted check
        gets wrong."""
        pdf_bytes = _encrypted_pdf_bytes(
            "owner protected only", user_password="", owner_password="OwnerSecret456"
        )
        response = await client.post(
            "/api/ingestion/check",
            headers=auth_headers,
            files={"files": ("owner-only.pdf", pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["files"] == [{"filename": "owner-only.pdf", "needs_password": False}]
