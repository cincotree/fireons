import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_api import require_admin
from database.models import JobRunStatus, User
from database.repository import JobRunRepository
from database.session import get_session
from jobs.launcher import launch_job
from jobs.registry import JOBS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])


class JobLaunchRequest(BaseModel):
    job: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobRunResponse(BaseModel):
    id: str
    job: str
    payload: dict[str, Any]
    status: str
    task_arn: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    @classmethod
    def from_run(cls, run) -> "JobRunResponse":
        return cls(
            id=run.id,
            job=run.job,
            payload=run.payload,
            status=run.status.value,
            task_arn=run.task_arn,
            error_message=run.error_message,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )


@router.get("", response_model=list[str])
async def list_jobs(_: User = Depends(require_admin)):
    return sorted(JOBS)


@router.post("/runs", response_model=JobRunResponse, status_code=201)
async def launch(
    request: JobLaunchRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if request.job not in JOBS:
        raise HTTPException(status_code=400, detail=f"Unknown job {request.job!r}")

    try:
        run_id = await launch_job(request.job, request.payload)
    except Exception:
        logger.exception("Could not launch job %s", request.job)
        raise HTTPException(status_code=502, detail="Could not start the job, see the run list for details")

    return JobRunResponse.from_run(await JobRunRepository(session).get(run_id))


@router.get("/runs", response_model=list[JobRunResponse])
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[JobRunStatus] = None,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    runs = await JobRunRepository(session).list_recent(limit, status)
    return [JobRunResponse.from_run(run) for run in runs]
