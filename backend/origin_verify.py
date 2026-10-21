import hmac

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

ORIGIN_VERIFY_HEADER = "x-origin-verify"
EXEMPT_PATHS = frozenset({"/health", "/api/health"})


class OriginVerifyMiddleware:
    def __init__(self, app: ASGIApp, secret: str):
        if not secret:
            raise ValueError("OriginVerifyMiddleware requires a non-empty secret")
        self.app = app
        self.secret = secret.encode("utf-8")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        provided = Headers(scope=scope).get(ORIGIN_VERIFY_HEADER, "").encode("utf-8")
        if not hmac.compare_digest(provided, self.secret):
            response = JSONResponse({"detail": "Forbidden"}, status_code=403)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
