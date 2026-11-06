from collections.abc import Awaitable, Callable
from typing import Any

from jobs.exchange_rate_sync import run_exchange_rate_sync

JobFunction = Callable[[dict[str, Any]], Awaitable[None]]


class UnknownJobError(KeyError):
    pass


async def exchange_rate_sync(payload: dict[str, Any]) -> None:
    await run_exchange_rate_sync()


JOBS: dict[str, JobFunction] = {
    "exchange_rate_sync": exchange_rate_sync,
}


def get_job(name: str) -> JobFunction:
    try:
        return JOBS[name]
    except KeyError as error:
        raise UnknownJobError(f"Unknown job {name!r}") from error
