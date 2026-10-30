from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Callable, Awaitable
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from api.account_api import router as account_router
from api.auth_api import router as auth_router
from api.health_api import router as health_router
from api.ingestion_disabled_api import router as ingestion_disabled_router
from app_config import AppSettings, get_app_settings
from jobs.config import get_exchange_rate_sync_settings
from jobs.exchange_rate_sync import sync_exchange_rates


@asynccontextmanager
async def lifespan(app: FastAPI):
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


async def rewrite_api_path(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    scope = request.scope
    path = scope["path"]
    if path == "/api" or path.startswith("/api/"):
        scope["path"] = path[len("/api") :] or "/"
        raw_path = scope.get("raw_path")
        if raw_path:
            scope["raw_path"] = raw_path[len(b"/api") :] or b"/"
    return await call_next(request)


def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_app_settings()

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(rewrite_api_path)

    app.include_router(auth_router)
    app.include_router(account_router)
    if settings.ingestion_test_enabled:
        from api.ingestion_test_api import router as ingestion_test_router

        app.include_router(ingestion_test_router)
    if settings.ingestion_enabled:
        from api.ingestion_api import router as ingestion_router

        app.include_router(ingestion_router)
    else:
        app.include_router(ingestion_disabled_router)
    app.include_router(health_router)

    return app


app = create_app()
