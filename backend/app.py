import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Callable, Awaitable
from contextlib import asynccontextmanager

from api.convert_currency_api import router as convert_router
from api.networth_api import router as networth_router
from api.auth_api import router as auth_router
from database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)

# Middleware to strip `/api` from the path
@app.middleware("http")
async def rewrite_api_path(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    if request.url.path.startswith("/api"):
        scope = request.scope
        scope["path"] = request.url.path[len("/api") :]
        request = Request(scope, request.receive)
    response = await call_next(request)
    return response

app.include_router(auth_router)
app.include_router(convert_router)
app.include_router(networth_router)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3020").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
