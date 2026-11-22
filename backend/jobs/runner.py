import asyncio
import json
import logging
import os
import sys

from database.repository import JobRunRepository
from database.session import session_context
from jobs.launcher import JOB_NAME_ENV, JOB_RUN_ID_ENV
from jobs.registry import get_job

logger = logging.getLogger(__name__)

JOB_PAYLOAD_ENV = "JOB_PAYLOAD"


async def load_run(environ: dict[str, str]) -> tuple[str, str, dict]:
    async with session_context() as session:
        repository = JobRunRepository(session)
        run_id = environ.get(JOB_RUN_ID_ENV)
        if run_id:
            run = await repository.get(run_id)
            if run is None:
                raise SystemExit(f"Job run {run_id} not found")
        else:
            name = environ.get(JOB_NAME_ENV)
            if not name:
                raise SystemExit(f"Set {JOB_RUN_ID_ENV} or {JOB_NAME_ENV}")
            payload = json.loads(environ.get(JOB_PAYLOAD_ENV) or "{}")
            run = await repository.create(name, payload)
        return run.id, run.job, run.payload


async def record_failure(run_id: str, error: Exception) -> None:
    try:
        async with session_context() as session:
            await JobRunRepository(session).mark_failed(run_id, f"{type(error).__name__}: {error}")
    except Exception:
        logger.exception("Could not record the failure of run %s", run_id)


async def execute(environ: dict[str, str]) -> int:
    run_id = None
    try:
        run_id, job, payload = await load_run(environ)
        async with session_context() as session:
            await JobRunRepository(session).mark_running(run_id)
        await get_job(job)(payload)
    except Exception as error:
        logger.exception("Job run %s failed", run_id or environ.get(JOB_NAME_ENV))
        if run_id:
            await record_failure(run_id, error)
        return 1

    async with session_context() as session:
        await JobRunRepository(session).mark_succeeded(run_id)
    return 0


def main(environ: dict[str, str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(execute(environ if environ is not None else dict(os.environ)))


if __name__ == "__main__":
    sys.exit(main())
