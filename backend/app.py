from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Callable, Awaitable
from contextlib import asynccontextmanager

from api.uiflow import router as flow_router
from api.transactions_api import router as transactions_router
from api.convert_currency_api import router as convert_router
from api.networth_api import router as networth_router
from api.auth_api import router as auth_router
from database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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
app.include_router(flow_router)
app.include_router(transactions_router)
app.include_router(convert_router)
app.include_router(networth_router)
