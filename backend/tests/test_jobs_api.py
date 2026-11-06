from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import app
from auth_utils import create_access_token
from database.models import JobRunStatus, User
from database.repository import JobRunRepository
from database.session import get_session
from jobs import launcher


async def make_user(session, name: str, superuser: bool) -> User:
    user = User(
        email=f"{name}@example.com",
        username=name,
        hashed_password="unused",
        is_superuser=superuser,
    )
    session.add(user)
    await session.flush()
    return user


def auth(user: User) -> dict:
    token = create_access_token({"sub": user.id, "username": user.username, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    async def override_get_session():
        yield session

    @asynccontextmanager
    async def shared_session_context():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    monkeypatch.setattr(launcher, "session_context", shared_session_context)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def superuser(session) -> User:
    return await make_user(session, "root_user", True)


@pytest_asyncio.fixture
async def regular_user(session) -> User:
    return await make_user(session, "plain_user", False)


@pytest.fixture
def started(monkeypatch):
    launched = []

    def fake_start_task(run_id: str) -> str:
        launched.append(run_id)
        return "arn:task/1"

    monkeypatch.setattr(launcher, "start_task", fake_start_task)
    return launched


ENDPOINTS = [
    ("get", "/admin/jobs", None),
    ("get", "/admin/jobs/runs", None),
    ("post", "/admin/jobs/runs", {"job": "exchange_rate_sync"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", ENDPOINTS)
async def test_requires_authentication(client, method, path, body):
    response = await client.request(method, path, json=body)

    assert response.status_code in (401, 403)


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", ENDPOINTS)
async def test_rejects_regular_users(client, regular_user, started, method, path, body):
    response = await client.request(method, path, json=body, headers=auth(regular_user))

    assert response.status_code == 403
    assert started == []


@pytest.mark.asyncio
async def test_lists_registered_jobs(client, superuser):
    response = await client.get("/admin/jobs", headers=auth(superuser))

    assert response.status_code == 200
    assert "exchange_rate_sync" in response.json()


@pytest.mark.asyncio
async def test_superuser_launches_a_job(client, superuser, started):
    response = await client.post(
        "/admin/jobs/runs",
        json={"job": "exchange_rate_sync", "payload": {"a": 1}},
        headers=auth(superuser),
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["job"], body["status"], body["payload"], body["task_arn"]) == (
        "exchange_rate_sync",
        "queued",
        {"a": 1},
        "arn:task/1",
    )
    assert started == [body["id"]]


@pytest.mark.asyncio
async def test_rejects_unknown_job(client, superuser, started):
    response = await client.post("/admin/jobs/runs", json={"job": "nope"}, headers=auth(superuser))

    assert response.status_code == 400
    assert started == []


@pytest.mark.asyncio
async def test_rejects_invalid_body(client, superuser):
    response = await client.post("/admin/jobs/runs", json={"job": ""}, headers=auth(superuser))

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_launch_failure_returns_502_and_records_the_failure(client, superuser, session, monkeypatch):
    def failing_start_task(run_id: str) -> str:
        raise RuntimeError("no capacity")

    monkeypatch.setattr(launcher, "start_task", failing_start_task)

    response = await client.post("/admin/jobs/runs", json={"job": "exchange_rate_sync"}, headers=auth(superuser))

    assert response.status_code == 502
    runs = await JobRunRepository(session).list_recent()
    assert runs[0].status is JobRunStatus.FAILED
    assert "no capacity" in runs[0].error_message


@pytest.mark.asyncio
async def test_lists_runs_newest_first_with_filter_and_limit(client, superuser, session):
    repository = JobRunRepository(session)
    first = await repository.create("exchange_rate_sync")
    await repository.mark_succeeded(first.id)
    second = await repository.create("exchange_rate_sync")
    await repository.mark_failed(second.id, "boom")
    third = await repository.create("exchange_rate_sync")
    headers = auth(superuser)

    everything = (await client.get("/admin/jobs/runs", headers=headers)).json()
    failed = (await client.get("/admin/jobs/runs?status=failed", headers=headers)).json()
    limited = (await client.get("/admin/jobs/runs?limit=1", headers=headers)).json()

    assert {run["id"] for run in everything} == {first.id, second.id, third.id}
    assert [run["id"] for run in failed] == [second.id]
    assert failed[0]["error_message"] == "boom"
    assert len(limited) == 1


@pytest.mark.asyncio
async def test_list_runs_validates_query(client, superuser):
    headers = auth(superuser)

    assert (await client.get("/admin/jobs/runs?limit=0", headers=headers)).status_code == 422
    assert (await client.get("/admin/jobs/runs?status=bogus", headers=headers)).status_code == 422


@pytest.mark.asyncio
async def test_me_reports_superuser_flag(client, superuser, regular_user):
    assert (await client.get("/auth/me", headers=auth(superuser))).json()["is_superuser"] is True
    assert (await client.get("/auth/me", headers=auth(regular_user))).json()["is_superuser"] is False
