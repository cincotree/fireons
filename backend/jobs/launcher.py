import asyncio
from functools import lru_cache

from database.repository import JobRunRepository
from database.session import session_context
from jobs.config import get_jobs_settings

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


def start_task(run_id: str) -> str:
    import boto3

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


async def launch_run(run_id: str) -> None:
    try:
        task_arn = await asyncio.to_thread(start_task, run_id)
    except Exception as error:
        async with session_context() as session:
            repository = JobRunRepository(session)
            await repository.mark_launched(run_id)
            await repository.mark_failed(run_id, f"Launch failed: {error}")
        raise

    async with session_context() as session:
        await JobRunRepository(session).mark_launched(run_id, task_arn)


async def launch_job(job: str, payload: dict | None = None) -> str:
    async with session_context() as session:
        run = await JobRunRepository(session).create(job, payload)
        run_id = run.id
    await launch_run(run_id)
    return run_id
