from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.config import settings

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def security_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    origin = request.headers.get("origin")
    if request.method in _UNSAFE_METHODS and origin and origin not in settings.cors_origins:
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": "origin_not_allowed",
                    "message": "The request origin is not allowed.",
                }
            },
        )

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response
