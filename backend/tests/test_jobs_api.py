from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import app
from auth_utils import create_access_token, create_admin_token, decode_admin_token, get_password_hash
from database.models import Admin, JobRunStatus, User
from database.repository import AdminRepository, JobRunRepository
from database.session import get_session
from jobs import launcher
from jobs.config import get_jobs_settings


ADMIN_PASSWORD = "correct-horse-battery"


async def make_admin(session, username: str = "root_admin") -> Admin:
    return await AdminRepository(session).create(username, get_password_hash(ADMIN_PASSWORD))


async def make_user(session, name: str) -> User:
    user = User(email=f"{name}@example.com", username=name, hashed_password=get_password_hash("user-password"))
    session.add(user)
    await session.flush()
    return user


def admin_headers(admin: Admin) -> dict:
    token = create_admin_token(admin.id, admin.username)
    return {"Authorization": f"Bearer {token}"}


def user_headers(user: User) -> dict:
    token = create_access_token({"sub": user.id, "username": user.username, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    monkeypatch.setenv("JOBS_RUN_LOCALLY", "false")
    get_jobs_settings.cache_clear()
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
async def admin(session) -> Admin:
    return await make_admin(session)


@pytest_asyncio.fixture
async def regular_user(session) -> User:
    return await make_user(session, "plain_user")


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
async def test_rejects_regular_user_tokens(client, regular_user, started, method, path, body):
    response = await client.request(method, path, json=body, headers=user_headers(regular_user))

    assert response.status_code == 401
    assert started == []


@pytest.mark.asyncio
async def test_lists_registered_jobs(client, admin):
    response = await client.get("/admin/jobs", headers=admin_headers(admin))

    assert response.status_code == 200
    assert "exchange_rate_sync" in response.json()


@pytest.mark.asyncio
async def test_admin_launches_a_job(client, admin, started):
    response = await client.post(
        "/admin/jobs/runs",
        json={"job": "exchange_rate_sync", "payload": {"a": 1}},
        headers=admin_headers(admin),
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
async def test_rejects_unknown_job(client, admin, started):
    response = await client.post("/admin/jobs/runs", json={"job": "nope"}, headers=admin_headers(admin))

    assert response.status_code == 400
    assert started == []


@pytest.mark.asyncio
async def test_rejects_invalid_body(client, admin):
    response = await client.post("/admin/jobs/runs", json={"job": ""}, headers=admin_headers(admin))

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_launch_failure_returns_502_and_records_the_failure(client, admin, session, monkeypatch):
    def failing_start_task(run_id: str) -> str:
        raise RuntimeError("no capacity")

    monkeypatch.setattr(launcher, "start_task", failing_start_task)

    response = await client.post("/admin/jobs/runs", json={"job": "exchange_rate_sync"}, headers=admin_headers(admin))

    assert response.status_code == 502
    runs = await JobRunRepository(session).list_recent()
    assert runs[0].id in response.json()["detail"]
    assert runs[0].status is JobRunStatus.FAILED
    assert "no capacity" in runs[0].error_message


@pytest.mark.asyncio
async def test_lists_runs_newest_first_with_filter_and_limit(client, admin, session):
    repository = JobRunRepository(session)
    first = await repository.create("exchange_rate_sync")
    await repository.mark_succeeded(first.id)
    second = await repository.create("exchange_rate_sync")
    await repository.mark_failed(second.id, "boom")
    third = await repository.create("exchange_rate_sync")
    headers = admin_headers(admin)

    everything = (await client.get("/admin/jobs/runs", headers=headers)).json()
    failed = (await client.get("/admin/jobs/runs?status=failed", headers=headers)).json()
    limited = (await client.get("/admin/jobs/runs?limit=1", headers=headers)).json()

    assert {run["id"] for run in everything} == {first.id, second.id, third.id}
    assert [run["id"] for run in failed] == [second.id]
    assert failed[0]["error_message"] == "boom"
    assert len(limited) == 1


@pytest.mark.asyncio
async def test_list_runs_validates_query(client, admin):
    headers = admin_headers(admin)

    assert (await client.get("/admin/jobs/runs?limit=0", headers=headers)).status_code == 422
    assert (await client.get("/admin/jobs/runs?status=bogus", headers=headers)).status_code == 422


@pytest.mark.asyncio
async def test_admin_login_returns_a_token_that_works(client, admin):
    response = await client.post("/admin/login", json={"username": admin.username, "password": ADMIN_PASSWORD})

    assert response.status_code == 200
    token = response.json()["access_token"]
    listed = await client.get("/admin/jobs", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("username,password", [
    ("root_admin", "wrong-password"),
    ("nobody", ADMIN_PASSWORD),
    ("root_admin", ""),
])
async def test_admin_login_rejects_bad_credentials(client, admin, username, password):
    response = await client.post("/admin/login", json={"username": username, "password": password})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_admin_login_validates_body(client):
    assert (await client.post("/admin/login", json={"username": "x"})).status_code == 422


@pytest.mark.asyncio
async def test_user_login_does_not_accept_admin_credentials(client, admin):
    response = await client.post("/auth/login", json={"username": admin.username, "password": ADMIN_PASSWORD})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_tokens_do_not_work_for_user_endpoints(client, admin):
    response = await client.get("/auth/me", headers=admin_headers(admin))

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_for_a_deleted_admin_is_rejected(client, admin, session):
    headers = admin_headers(admin)
    await session.delete(admin)
    await session.flush()

    assert (await client.get("/admin/jobs", headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_role_only_token_without_audience_is_rejected(client, admin):
    token = create_access_token({"sub": admin.id, "username": admin.username, "role": "admin"})

    response = await client.get("/admin/jobs", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_token_has_the_admin_audience_and_short_lifetime(client, admin):
    response = await client.post("/admin/login", json={"username": admin.username, "password": ADMIN_PASSWORD})

    assert decode_admin_token(response.json()["access_token"]) == admin.id


@pytest.mark.asyncio
async def test_garbage_token_is_rejected(client):
    response = await client.get("/admin/jobs", headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 401
