import json
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from sqlalchemy import select

from database.models import JobRun, JobRunStatus
from database.repository import JobRunRepository
from jobs import launcher, registry, runner
from jobs.config import get_jobs_settings


@pytest.fixture(autouse=True)
def shared_session(monkeypatch, session):
    @asynccontextmanager
    async def fake_session_context():
        yield session

    for module in (runner, launcher):
        monkeypatch.setattr(module, "session_context", fake_session_context)


@pytest_asyncio.fixture
async def repository(session):
    return JobRunRepository(session)


@pytest.fixture
def calls():
    return []


@pytest.fixture
def fake_jobs(monkeypatch, calls):
    async def ok(payload):
        calls.append(payload)

    async def boom(payload):
        raise ValueError("boom")

    monkeypatch.setattr(registry, "JOBS", {"ok": ok, "boom": boom})


@pytest.fixture
def jobs_settings(monkeypatch):
    monkeypatch.setenv("JOBS_ECS_CLUSTER_ARN", "arn:cluster")
    monkeypatch.setenv("JOBS_ECS_TASK_DEFINITION", "fireons-jobs")
    monkeypatch.setenv("JOBS_ECS_SUBNETS", "subnet-a, subnet-b")
    monkeypatch.setenv("JOBS_ECS_SECURITY_GROUPS", "sg-1")
    get_jobs_settings.cache_clear()
    yield
    get_jobs_settings.cache_clear()


class FakeEcs:
    def __init__(self, response=None):
        self.response = response or {"tasks": [{"taskArn": "arn:task/1"}], "failures": []}
        self.calls = []

    def run_task(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


@pytest.fixture
def ecs(monkeypatch, jobs_settings):
    import boto3

    client = FakeEcs()
    monkeypatch.setattr(boto3, "client", lambda name, *a, **k: client)
    return client


def test_registry_knows_exchange_rate_sync():
    assert registry.get_job("exchange_rate_sync")


def test_registry_rejects_unknown_job():
    with pytest.raises(registry.UnknownJobError):
        registry.get_job("nope")


@pytest.mark.asyncio
async def test_runner_executes_existing_run_and_marks_succeeded(fake_jobs, calls, repository):
    run = await repository.create("ok", {"a": 1})

    code = await runner.execute({"JOB_RUN_ID": run.id})

    assert code == 0
    assert calls == [{"a": 1}]
    assert run.status is JobRunStatus.SUCCEEDED
    assert run.started_at is not None and run.completed_at is not None


@pytest.mark.asyncio
async def test_runner_marks_failed_and_returns_nonzero(fake_jobs, repository):
    run = await repository.create("boom")

    code = await runner.execute({"JOB_RUN_ID": run.id})

    assert code == 1
    assert run.status is JobRunStatus.FAILED
    assert run.error_message == "ValueError: boom"


@pytest.mark.asyncio
async def test_runner_records_unknown_job_as_failed(fake_jobs, repository):
    run = await repository.create("missing")

    assert await runner.execute({"JOB_RUN_ID": run.id}) == 1
    assert run.status is JobRunStatus.FAILED


@pytest.mark.asyncio
async def test_runner_creates_run_for_scheduled_invocation(fake_jobs, calls, session):
    code = await runner.execute({"JOB_NAME": "ok", "JOB_PAYLOAD": json.dumps({"z": 1})})

    assert code == 0
    assert calls == [{"z": 1}]
    run = (await session.execute(select(JobRun))).scalar_one()
    assert (run.job, run.status) == ("ok", JobRunStatus.SUCCEEDED)


@pytest.mark.asyncio
async def test_runner_requires_run_id_or_job_name(fake_jobs):
    with pytest.raises(SystemExit):
        await runner.execute({})


@pytest.mark.asyncio
async def test_runner_rejects_missing_run(fake_jobs):
    with pytest.raises(SystemExit):
        await runner.execute({"JOB_RUN_ID": "00000000-0000-0000-0000-000000000000"})


@pytest.mark.asyncio
async def test_launch_job_creates_run_and_starts_task(ecs, repository):
    run_id = await launcher.launch_job("ok", {"n": 5})

    run = await repository.get(run_id)
    assert (run.job, run.payload, run.status) == ("ok", {"n": 5}, JobRunStatus.QUEUED)
    assert run.task_arn == "arn:task/1"
    call = ecs.calls[0]
    assert call["cluster"] == "arn:cluster"
    assert call["taskDefinition"] == "fireons-jobs"
    assert call["launchType"] == "FARGATE"
    network = call["networkConfiguration"]["awsvpcConfiguration"]
    assert network["subnets"] == ["subnet-a", "subnet-b"]
    assert network["securityGroups"] == ["sg-1"]
    environment = call["overrides"]["containerOverrides"][0]["environment"]
    assert environment == [{"name": "JOB_RUN_ID", "value": run_id}]


@pytest.mark.asyncio
async def test_launch_failure_marks_run_failed(monkeypatch, jobs_settings, session):
    import boto3

    client = FakeEcs({"tasks": [], "failures": [{"reason": "CAPACITY"}]})
    monkeypatch.setattr(boto3, "client", lambda name, *a, **k: client)

    with pytest.raises(RuntimeError, match="RunTask failed"):
        await launcher.launch_job("ok")

    run = (await session.execute(select(JobRun))).scalar_one()
    assert run.status is JobRunStatus.FAILED
    assert "Launch failed" in run.error_message


@pytest.mark.asyncio
async def test_launch_requires_configuration(monkeypatch, repository):
    monkeypatch.delenv("JOBS_ECS_CLUSTER_ARN", raising=False)
    monkeypatch.delenv("JOBS_ECS_TASK_DEFINITION", raising=False)
    get_jobs_settings.cache_clear()

    with pytest.raises(RuntimeError, match="not configured"):
        await launcher.launch_job("ok")


@pytest.mark.asyncio
async def test_launch_run_relaunches_a_failed_run(ecs, repository):
    run = await repository.create("ok")
    await repository.mark_failed(run.id, "x")

    await launcher.launch_run(run.id)

    assert run.status is JobRunStatus.QUEUED
    assert run.error_message is None
    assert run.completed_at is None
    assert run.task_arn == "arn:task/1"
