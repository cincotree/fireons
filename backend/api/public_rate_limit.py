import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request

PUBLIC_READ_LIMIT = 120
PUBLIC_READ_WINDOW_SECONDS = 60


class SlidingWindowLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> float | None:
        now = self._clock()
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return max(hits[0] + self.window_seconds - now, 1.0)
        hits.append(now)
        return None

    def reset(self) -> None:
        self._hits.clear()


public_read_limiter = SlidingWindowLimiter(PUBLIC_READ_LIMIT, PUBLIC_READ_WINDOW_SECONDS)


async def limit_public_reads(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    retry_after = public_read_limiter.check(key)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again shortly.",
            headers={"Retry-After": str(int(retry_after))},
        )
