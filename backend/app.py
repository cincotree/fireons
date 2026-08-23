from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Callable, Awaitable
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from api.account_api import router as account_router
from api.auth_api import router as auth_router
from api.ingestion_test_api import router as ingestion_test_router
from api.ingestion_api import router as ingestion_router
from database.session import init_db
from jobs.config import get_exchange_rate_sync_settings
from jobs.exchange_rate_sync import sync_exchange_rates


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    scheduler = None
    settings = get_exchange_rate_sync_settings()
    if settings.exchange_rate_sync_enabled:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            sync_exchange_rates,
            trigger=CronTrigger(
                hour=settings.exchange_rate_sync_hour_utc,
                minute=settings.exchange_rate_sync_minute_utc,
            ),
            id="nightly_exchange_rate_sync",
            replace_existing=True,
        )
        scheduler.start()

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3020"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rewrite_api_path(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    if request.url.path.startswith("/api"):
        scope = request.scope
        scope["path"] = request.url.path[len("/api") :]
        request = Request(scope, request.receive)
    response = await call_next(request)
    return response

app.include_router(auth_router)
app.include_router(account_router)
app.include_router(ingestion_test_router)
app.include_router(ingestion_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
