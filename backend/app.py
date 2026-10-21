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
from app_config import AppSettings, get_app_settings, validate_startup_settings
from database.config import Settings as DatabaseSettings
from database.config import get_settings as get_database_settings
from database.session import init_db
from jobs.config import get_exchange_rate_sync_settings
from jobs.exchange_rate_sync import sync_exchange_rates
from origin_verify import OriginVerifyMiddleware
from ssm_secrets import load_ssm_parameters


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


async def rewrite_api_path(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    if request.url.path.startswith("/api"):
        scope = request.scope
        scope["path"] = request.url.path[len("/api") :]
        request = Request(scope, request.receive)
    response = await call_next(request)
    return response


async def health():
    return {"status": "ok"}


def create_app(
    settings: AppSettings | None = None,
    database_settings: DatabaseSettings | None = None,
) -> FastAPI:
    settings = settings or get_app_settings()
    database_settings = database_settings or get_database_settings()
    validate_startup_settings(settings, database_settings)

    docs_enabled = settings.api_docs_routes_enabled
    app = FastAPI(
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.origin_verify_secret:
        app.add_middleware(OriginVerifyMiddleware, secret=settings.origin_verify_secret)
    app.middleware("http")(rewrite_api_path)

    app.include_router(auth_router)
    app.include_router(account_router)
    if settings.ingestion_test_router_enabled:
        app.include_router(ingestion_test_router)
    app.include_router(ingestion_router)
    app.get("/health")(health)

    return app


load_ssm_parameters()
app = create_app()
