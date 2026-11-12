import json
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from sqlalchemy import select

from database.models import JobRun, JobRunStatus
from database.repository import JobRunRepository
from database.repository import JobRunNotFoundError, JobRunRepository
from jobs import launcher, registry, runner
from jobs.config import get_jobs_settings


@pytest.fixture(autouse=True)
def isolated_jobs_settings(monkeypatch):
    monkeypatch.setenv("JOBS_RUN_LOCALLY", "false")
    monkeypatch.setenv("APP_ENV", "")
    get_jobs_settings.cache_clear()
    launcher.find_network.cache_clear()
    yield
    get_jobs_settings.cache_clear()
    launcher.find_network.cache_clear()


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
    monkeypatch.setenv("APP_ENV", "production")
    get_jobs_settings.cache_clear()
    launcher.find_network.cache_clear()
    yield
    get_jobs_settings.cache_clear()
    launcher.find_network.cache_clear()


class FakeEc2:
    def __init__(self, subnets=("subnet-a", "subnet-b"), groups=("sg-1",)):
        self.subnets = subnets
        self.groups = groups
        self.calls = []

    def describe_subnets(self, **kwargs):
        self.calls.append(("subnets", kwargs))
        return {"Subnets": [{"SubnetId": value} for value in self.subnets]}

    def describe_security_groups(self, **kwargs):
        self.calls.append(("groups", kwargs))
        return {"SecurityGroups": [{"GroupId": value} for value in self.groups]}


class FakeEcs:
    def __init__(self, response=None):
        self.response = response or {"tasks": [{"taskArn": "arn:task/1"}], "failures": []}
        self.calls = []

    def run_task(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def patch_boto3(monkeypatch, ecs, ec2=None):
    import boto3

    clients = {"ecs": ecs, "ec2": ec2 or FakeEc2()}
    monkeypatch.setattr(boto3, "client", lambda name, *a, **k: clients[name])


@pytest.fixture
def ecs(monkeypatch, jobs_settings):
    client = FakeEcs()
    patch_boto3(monkeypatch, client)
    return client


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
    assert call["cluster"] == "fireons-production-jobs"
    assert call["taskDefinition"] == "fireons-production-jobs"
    assert call["launchType"] == "FARGATE"
    network = call["networkConfiguration"]["awsvpcConfiguration"]
    assert network["subnets"] == ["subnet-a", "subnet-b"]
    assert network["securityGroups"] == ["sg-1"]
    environment = call["overrides"]["containerOverrides"][0]["environment"]
    assert environment == [{"name": "JOB_RUN_ID", "value": run_id}]


@pytest.mark.asyncio
async def test_launch_failure_marks_run_failed(monkeypatch, jobs_settings, session):
    client = FakeEcs({"tasks": [], "failures": [{"reason": "CAPACITY"}]})
    patch_boto3(monkeypatch, client)

    with pytest.raises(launcher.LaunchError, match="RunTask failed") as raised:
        await launcher.launch_job("ok")

    run = (await session.execute(select(JobRun))).scalar_one()
    assert raised.value.run_id == run.id
    assert run.status is JobRunStatus.FAILED
    assert "Launch failed" in run.error_message
    assert run.completed_at is not None


@pytest.mark.asyncio
async def test_local_mode_runs_the_runner_in_a_subprocess(monkeypatch, repository):
    monkeypatch.setenv("JOBS_RUN_LOCALLY", "true")
    get_jobs_settings.cache_clear()
    spawned = {}

    class FakeProcess:
        pid = 4242

    def fake_popen(command, cwd, env):
        spawned.update(command=command, cwd=cwd, env=env)
        return FakeProcess()

    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)

    run_id = await launcher.launch_job("ok")

    run = await repository.get(run_id)
    assert run.task_arn == "local:4242"
    assert spawned["command"][1:] == ["-m", "jobs.runner"]
    assert spawned["env"]["JOB_RUN_ID"] == run_id
    assert (spawned["cwd"] / "jobs" / "runner.py").exists()
    get_jobs_settings.cache_clear()


@pytest.mark.asyncio
async def test_launch_fails_when_network_is_not_found(monkeypatch, jobs_settings, repository):
    patch_boto3(monkeypatch, FakeEcs(), FakeEc2(groups=()))

    with pytest.raises(launcher.LaunchError, match="fireons-production-jobs"):
        await launcher.launch_job("ok")


@pytest.mark.asyncio
async def test_network_lookup_is_cached(monkeypatch, jobs_settings, repository):
    ec2 = FakeEc2()
    patch_boto3(monkeypatch, FakeEcs(), ec2)

    await launcher.launch_job("ok")
    await launcher.launch_job("ok")

    assert len(ec2.calls) == 2


@pytest.mark.asyncio
async def test_launch_requires_configuration(monkeypatch, repository):
    get_jobs_settings.cache_clear()

    with pytest.raises(launcher.LaunchError, match="not configured"):
        await launcher.launch_job("ok")


@pytest.mark.asyncio
async def test_launch_run_resets_the_run_before_starting_the_task(monkeypatch, repository):
    run = await repository.create("ok")
    await repository.mark_running(run.id)
    await repository.mark_failed(run.id, "old failure")
    seen = {}

    def fake_start_task(run_id: str) -> str:
        seen["status"] = run.status
        seen["error"] = run.error_message
        seen["completed_at"] = run.completed_at
        return "arn:task/9"

    monkeypatch.setattr(launcher, "start_task", fake_start_task)

    await launcher.launch_run(run.id)

    assert seen == {"status": JobRunStatus.QUEUED, "error": None, "completed_at": None}
    assert run.task_arn == "arn:task/9"


@pytest.mark.asyncio
async def test_recording_the_task_arn_does_not_overwrite_runner_progress(repository):
    run = await repository.create("ok")
    await repository.mark_running(run.id)
    await repository.mark_succeeded(run.id)
    completed_at = run.completed_at

    await repository.set_task_arn(run.id, "local:123")
    await repository.session.refresh(run)

    assert run.status is JobRunStatus.SUCCEEDED
    assert run.completed_at == completed_at
    assert run.started_at is not None
    assert run.task_arn == "local:123"


@pytest.mark.asyncio
async def test_launch_failure_keeps_the_original_error_when_recording_it_fails(monkeypatch, ecs, repository):
    ecs.response = {"tasks": [], "failures": [{"reason": "CAPACITY"}]}
    run = await repository.create("ok")

    async def broken_mark_failed(self, run_id, message):
        raise RuntimeError("database down")

    monkeypatch.setattr(JobRunRepository, "mark_failed", broken_mark_failed)

    with pytest.raises(launcher.LaunchError, match="CAPACITY") as raised:
        await launcher.launch_run(run.id)

    assert raised.value.run_id == run.id


@pytest.mark.asyncio
@pytest.mark.parametrize("method,args", [
    ("mark_running", ()),
    ("mark_succeeded", ()),
    ("mark_failed", ("x",)),
    ("reset_for_launch", ()),
    ("set_task_arn", ("arn",)),
])
async def test_repository_raises_a_clear_error_for_unknown_runs(repository, method, args):
    with pytest.raises(JobRunNotFoundError, match="not found"):
        await getattr(repository, method)("00000000-0000-0000-0000-000000000000", *args)


@pytest.mark.asyncio
async def test_runner_marks_the_run_failed_when_starting_it_fails(monkeypatch, fake_jobs, repository):
    run = await repository.create("ok")

    async def broken_mark_running(self, run_id):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(JobRunRepository, "mark_running", broken_mark_running)

    code = await runner.execute({"JOB_RUN_ID": run.id})

    assert code == 1
    assert run.status is JobRunStatus.FAILED
    assert "database hiccup" in run.error_message


@pytest.mark.asyncio
async def test_runner_survives_a_failure_it_cannot_record(monkeypatch, fake_jobs, repository):
    run = await repository.create("boom")

    async def broken_mark_failed(self, run_id, message):
        raise RuntimeError("database down")

    monkeypatch.setattr(JobRunRepository, "mark_failed", broken_mark_failed)

    assert await runner.execute({"JOB_RUN_ID": run.id}) == 1


@pytest.mark.asyncio
async def test_runner_returns_failure_for_an_invalid_payload_without_a_run(fake_jobs, session):
    code = await runner.execute({"JOB_NAME": "ok", "JOB_PAYLOAD": "{not json"})

    assert code == 1
    assert (await session.execute(select(JobRun))).scalars().all() == []


@pytest.mark.asyncio
async def test_scheduled_run_is_marked_failed_when_starting_it_fails(monkeypatch, fake_jobs, session):
    async def broken_mark_running(self, run_id):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(JobRunRepository, "mark_running", broken_mark_running)

    code = await runner.execute({"JOB_NAME": "ok"})

    run = (await session.execute(select(JobRun))).scalar_one()
    assert code == 1
    assert run.status is JobRunStatus.FAILED
