import time
from collections import defaultdict

from fastapi import HTTPException

# In-memory, single-instance — fine for this app's personal-use, single-server
# deployment (same category of simplification as the hardcoded eval fallbacks in
# extract.py/pipeline.py). Resets on server restart; would need a shared store
# (e.g. Redis) if this ever ran behind multiple worker processes.
#
# Cumulative byte volume is the primary guard — cost tracks with how much gets sent
# to the LLM, not how many HTTP requests it took to send it, and a legitimate
# first-time setup (15-20 statements in one sitting) is a request-count spike but a
# modest byte volume. MAX_UPLOADS_PER_WINDOW is just a loose backstop against a
# runaway loop of tiny files; it should never be the one that fires in normal use.
WINDOW_SECONDS = 3600
MAX_UPLOADS_PER_WINDOW = 40
MAX_CUMULATIVE_BYTES_PER_WINDOW = 200 * 1024 * 1024

_upload_log: dict[str, list[tuple[float, int]]] = defaultdict(list)


def check_rate_limit(user_id: str, file_size_bytes: int) -> None:
    now = time.monotonic()
    window_start = now - WINDOW_SECONDS
    log = _upload_log[user_id]
    log[:] = [(t, size) for t, size in log if t > window_start]

    if len(log) >= MAX_UPLOADS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail=f"Too many uploads — limit is {MAX_UPLOADS_PER_WINDOW} per "
            f"{WINDOW_SECONDS // 60} minutes. Try again shortly.",
        )

    cumulative_bytes = sum(size for _, size in log) + file_size_bytes
    if cumulative_bytes > MAX_CUMULATIVE_BYTES_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail=f"Upload volume limit reached — "
            f"{MAX_CUMULATIVE_BYTES_PER_WINDOW // (1024 * 1024)}MB per "
            f"{WINDOW_SECONDS // 60} minutes. Try again shortly.",
        )

    log.append((now, file_size_bytes))
