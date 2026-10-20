import json
import shutil
import tempfile
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from pypdf import PasswordType, PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_api import get_current_user
from database.models import User
from database.repository import IngestionRunRepository
from database.session import get_session
from ingestion.background import run_ingestion
from ingestion.rate_limit import check_rate_limit

router = APIRouter(prefix="", tags=["ingestion"])

MAX_STATEMENT_SIZE_BYTES = 15 * 1024 * 1024


class FileCheckResult(BaseModel):
    filename: str
    needs_password: bool


class IngestionCheckResponse(BaseModel):
    files: list[FileCheckResult]


class IngestionUploadResponse(BaseModel):
    run_id: str


class IngestionRunResponse(BaseModel):
    id: str
    status: str
    file_count: int
    positions_count: int | None
    warnings: list[str] | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    llm_call_count: int | None
    llm_input_tokens: int | None
    llm_output_tokens: int | None
    llm_cache_creation_tokens: int | None
    llm_cache_read_tokens: int | None
    llm_estimated_cost_usd: Decimal | None


@router.post("/ingestion/check", response_model=IngestionCheckResponse)
async def check_statements(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    """Cheap, stateless probe — reports which files are password-protected so the
    UI can ask for a password only where one is actually needed, before starting a
    real (rate-limited, billable) import. Never persists anything."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []
    for file in files:
        content = await file.read()
        if len(content) > MAX_STATEMENT_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"{file.filename} is too large")
        try:
            reader = PdfReader(BytesIO(content))
            # is_encrypted alone over-reports: many real statements are
            # "encrypted" only with an owner password (restricts printing/
            # editing) and an empty user password, so they open with no
            # password at all. Only ask the user for one if an empty
            # password genuinely fails to unlock it.
            needs_password = reader.is_encrypted and reader.decrypt("") == PasswordType.NOT_DECRYPTED
        except Exception:
            # Not a valid PDF at all — let the real upload's PdfReadError quarantine
            # path surface that clearly, rather than mislabeling it here.
            needs_password = False
        results.append(FileCheckResult(filename=file.filename, needs_password=needs_password))

    return IngestionCheckResponse(files=results)


@router.post("/ingestion/upload", response_model=IngestionUploadResponse, status_code=202)
async def upload_statements(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    passwords: str = Form("{}"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    filenames = [file.filename for file in files]
    if len(filenames) != len(set(filenames)):
        raise HTTPException(
            status_code=400,
            detail="Two uploaded files have the same name — rename one and try again",
        )

    try:
        password_map: dict[str, str] = json.loads(passwords) if passwords else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid passwords payload")

    # Written into one per-request temp directory, under each file's ORIGINAL
    # filename (not a random tempfile name) — ingest()'s passwords dict is keyed
    # by filename, and it reads that key off Path.name, so the two need to match.
    tmpdir = Path(tempfile.mkdtemp())
    file_paths: list[Path] = []
    try:
        for file in files:
            content = await file.read()
            if len(content) > MAX_STATEMENT_SIZE_BYTES:
                raise HTTPException(status_code=413, detail=f"{file.filename} is too large")
            check_rate_limit(current_user.id, len(content))
            path = tmpdir / file.filename
            path.write_bytes(content)
            file_paths.append(path)
    except HTTPException:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise

    run = await IngestionRunRepository(session).create(
        user_id=current_user.id, file_count=len(file_paths)
    )
    await session.commit()

    background_tasks.add_task(
        run_ingestion,
        run.id,
        current_user.id,
        file_paths,
        None,
        current_user.primary_currency,
        password_map,
    )

    return IngestionUploadResponse(run_id=run.id)


@router.get("/ingestion/runs/{run_id}", response_model=IngestionRunResponse)
async def get_ingestion_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    run = await IngestionRunRepository(session).get_by_id(run_id, current_user.id)
    if run is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    return IngestionRunResponse(
        id=run.id,
        status=run.status.value,
        file_count=run.file_count,
        positions_count=run.positions_count,
        warnings=run.warnings,
        error_message=run.error_message,
        created_at=run.created_at,
        completed_at=run.completed_at,
        llm_call_count=run.llm_call_count,
        llm_input_tokens=run.llm_input_tokens,
        llm_output_tokens=run.llm_output_tokens,
        llm_cache_creation_tokens=run.llm_cache_creation_tokens,
        llm_cache_read_tokens=run.llm_cache_read_tokens,
        llm_estimated_cost_usd=run.llm_estimated_cost_usd,
    )
