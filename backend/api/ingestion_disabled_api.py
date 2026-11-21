from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["ingestion"])


@router.api_route("/ingestion/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def ingestion_disabled(path: str):
    raise HTTPException(status_code=503, detail="Statement ingestion is not available yet")
