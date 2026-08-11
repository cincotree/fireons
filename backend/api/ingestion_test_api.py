import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from api.auth_api import get_current_user
from database.models import User
from ingestion.model import NetWorth
from ingestion.pipeline import ingest
from ingestion.rate_limit import check_rate_limit

router = APIRouter(prefix="", tags=["ingestion-test"])

MAX_STATEMENT_SIZE_BYTES = 15 * 1024 * 1024


@router.post("/ingestion-test/upload")
async def test_ingest_upload(
    file: UploadFile = File(...),
    password: str = Form(""),
    current_user: User = Depends(get_current_user),
):
    check_rate_limit(current_user.id)

    content = await file.read()
    if len(content) > MAX_STATEMENT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File is too large")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    empty = NetWorth(as_of=None, reporting_currency="INR", positions={}, total="0")
    try:
        result = ingest(
            empty,
            [tmp_path],
            password=password or None,
            account_owner_name=current_user.full_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return result.model_dump(mode="json")
