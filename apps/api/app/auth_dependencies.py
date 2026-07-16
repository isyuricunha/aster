from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_service import AuthContext, LoginRateLimiter, PasswordService, SessionService
from app.config import settings
from app.db import get_session


@lru_cache
def get_password_service() -> PasswordService:
    return PasswordService()


@lru_cache
def get_session_service() -> SessionService:
    return SessionService()


@lru_cache
def get_login_rate_limiter() -> LoginRateLimiter:
    return LoginRateLimiter()


DatabaseSession = Annotated[AsyncSession, Depends(get_session)]
PasswordManager = Annotated[PasswordService, Depends(get_password_service)]
SessionManager = Annotated[SessionService, Depends(get_session_service)]
LoginLimiter = Annotated[LoginRateLimiter, Depends(get_login_rate_limiter)]


async def get_optional_auth(
    request: Request,
    database: DatabaseSession,
    sessions: SessionManager,
) -> AuthContext | None:
    token = request.cookies.get(settings.aster_session_cookie_name)
    return await sessions.resolve(database, token)


OptionalAuth = Annotated[AuthContext | None, Depends(get_optional_auth)]


async def require_auth(context: OptionalAuth) -> AuthContext:
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "Authentication required."},
        )
    return context


RequiredAuth = Annotated[AuthContext, Depends(require_auth)]
