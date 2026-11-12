import asyncio
import logging
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from database.repository import JobRunRepository
from database.session import session_context
from jobs.config import get_jobs_settings

logger = logging.getLogger(__name__)

CONTAINER_NAME = "jobs"
JOB_RUN_ID_ENV = "JOB_RUN_ID"
JOB_NAME_ENV = "JOB_NAME"


@lru_cache
def find_network(name: str) -> tuple[list[str], list[str]]:
    import boto3

    ec2 = boto3.client("ec2")
    subnets = ec2.describe_subnets(Filters=[{"Name": "default-for-az", "Values": ["true"]}])["Subnets"]
    groups = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [name]}])["SecurityGroups"]
    if not subnets or not groups:
        raise RuntimeError(f"No default subnets or security group named {name!r} found")
    return [subnet["SubnetId"] for subnet in subnets], [group["GroupId"] for group in groups]


def start_local_process(run_id: str) -> str:
    process = subprocess.Popen(
        [sys.executable, "-m", "jobs.runner"],
        cwd=Path(__file__).resolve().parent.parent,
        env={**os.environ, JOB_RUN_ID_ENV: run_id},
    )
    return f"local:{process.pid}"


def start_task(run_id: str) -> str:
    import boto3

    if get_jobs_settings().jobs_run_locally:
        return start_local_process(run_id)

    name = get_jobs_settings().jobs_name
    subnets, security_groups = find_network(name)

    response = boto3.client("ecs").run_task(
        cluster=name,
        taskDefinition=name,
        launchType="FARGATE",
        count=1,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": security_groups,
                "assignPublicIp": "ENABLED",
            }
        },
        overrides={
            "containerOverrides": [
                {"name": CONTAINER_NAME, "environment": [{"name": JOB_RUN_ID_ENV, "value": run_id}]}
            ]
        },
    )

    failures = response.get("failures") or []
    if failures or not response.get("tasks"):
        raise RuntimeError(f"RunTask failed: {failures}")
    return response["tasks"][0]["taskArn"]


class LaunchError(RuntimeError):
    def __init__(self, run_id: str, reason: str):
        super().__init__(reason)
        self.run_id = run_id


async def launch_run(run_id: str) -> None:
    async with session_context() as session:
        await JobRunRepository(session).reset_for_launch(run_id)

    try:
        task_arn = await asyncio.to_thread(start_task, run_id)
    except Exception as error:
        try:
            async with session_context() as session:
                await JobRunRepository(session).mark_failed(run_id, f"Launch failed: {error}")
        except Exception:
            logger.exception("Could not record the launch failure for run %s", run_id)
        raise LaunchError(run_id, str(error)) from error

    async with session_context() as session:
        await JobRunRepository(session).set_task_arn(run_id, task_arn)


async def launch_job(job: str, payload: dict | None = None) -> str:
    async with session_context() as session:
        run = await JobRunRepository(session).create(job, payload)
        run_id = run.id
    await launch_run(run_id)
    return run_id
