import time
from collections import defaultdict

from fastapi import HTTPException

# In-memory, single-instance — fine for this app's personal-use, single-server
# deployment (same category of simplification as the hardcoded eval fallbacks in
# extract.py/pipeline.py). Resets on server restart; would need a shared store
# (e.g. Redis) if this ever ran behind multiple worker processes.
WINDOW_SECONDS = 600
MAX_UPLOADS_PER_WINDOW = 10

_upload_log: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(user_id: str) -> None:
    now = time.monotonic()
    window_start = now - WINDOW_SECONDS
    timestamps = _upload_log[user_id]
    timestamps[:] = [t for t in timestamps if t > window_start]
    if len(timestamps) >= MAX_UPLOADS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail=f"Too many uploads — limit is {MAX_UPLOADS_PER_WINDOW} per "
            f"{WINDOW_SECONDS // 60} minutes. Try again shortly.",
        )
    timestamps.append(now)
