from contextlib import asynccontextmanager

import pytest

from auth_utils import verify_password
from database.repository import AdminRepository
from scripts import create_admin as cli


@pytest.fixture(autouse=True)
def shared_session(monkeypatch, session):
    @asynccontextmanager
    async def fake_session_context():
        yield session

    monkeypatch.setattr(cli, "session_context", fake_session_context)


@pytest.mark.asyncio
async def test_creates_an_admin_with_a_hashed_password(session):
    await cli.create_admin("  ops_admin  ", "a-long-enough-password")

    admin = await AdminRepository(session).get_by_username("ops_admin")
    assert admin is not None
    assert admin.hashed_password != "a-long-enough-password"
    assert verify_password("a-long-enough-password", admin.hashed_password)


@pytest.mark.asyncio
async def test_rejects_short_passwords(session):
    with pytest.raises(ValueError, match="at least"):
        await cli.create_admin("ops_admin", "short")

    assert await AdminRepository(session).get_by_username("ops_admin") is None


@pytest.mark.asyncio
async def test_rejects_blank_username():
    with pytest.raises(ValueError, match="Username"):
        await cli.create_admin("   ", "a-long-enough-password")


@pytest.mark.asyncio
async def test_rejects_duplicate_usernames():
    await cli.create_admin("ops_admin", "a-long-enough-password")

    with pytest.raises(ValueError, match="already exists"):
        await cli.create_admin("ops_admin", "another-long-password")


def test_read_password_prefers_environment(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "from-the-environment")

    assert cli.read_password() == "from-the-environment"


def test_read_password_requires_matching_confirmation(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    answers = iter(["first-password-1", "second-password"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: next(answers))

    with pytest.raises(ValueError, match="do not match"):
        cli.read_password()
