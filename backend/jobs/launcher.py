import asyncio

from database.repository import JobRunRepository
from database.session import session_context
from jobs.config import get_jobs_settings

CONTAINER_NAME = "jobs"
JOB_RUN_ID_ENV = "JOB_RUN_ID"
JOB_NAME_ENV = "JOB_NAME"


def start_task(run_id: str) -> str:
    import boto3

    settings = get_jobs_settings()
    if not settings.jobs_ecs_cluster_arn or not settings.jobs_ecs_task_definition:
        raise RuntimeError("Fargate jobs are not configured")

    response = boto3.client("ecs").run_task(
        cluster=settings.jobs_ecs_cluster_arn,
        taskDefinition=settings.jobs_ecs_task_definition,
        launchType="FARGATE",
        count=1,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": settings.ecs_subnet_list,
                "securityGroups": settings.ecs_security_group_list,
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
