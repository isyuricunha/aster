from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import (
    get_login_rate_limiter,
    get_optional_auth,
    get_password_service,
    get_session_service,
    require_auth,
)
from app.auth_schemas import (
    AuthStatusResponse,
    AuthUserResponse,
    LoginRequest,
    PasswordChangeRequest,
    SessionRevocationResponse,
    SetupRequest,
)
from app.auth_service import (
    AuthContext,
    LoginRateLimiter,
    PasswordService,
    SessionService,
    session_cookie_options,
    utc_now,
)
from app.config import settings
from app.db import get_session
from app.models import AuthSession, User

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(value=token, **session_cookie_options())


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.aster_session_cookie_name,
        path="/",
        secure=settings.aster_session_secure,
        httponly=True,
        samesite="lax",
    )


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(
    database: AsyncSession = Depends(get_session),
    context: AuthContext | None = Depends(get_optional_auth),
) -> AuthStatusResponse:
    user_count = await database.scalar(select(func.count()).select_from(User))
    setup_required = not bool(user_count)
    return AuthStatusResponse(
        setup_required=setup_required,
        authenticated=context is not None,
        username=context.user.username if context else None,
    )


@router.post("/setup", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
async def setup_owner(
    payload: SetupRequest,
    response: Response,
    database: AsyncSession = Depends(get_session),
    passwords: PasswordService = Depends(get_password_service),
    sessions: SessionService = Depends(get_session_service),
) -> AuthUserResponse:
    if await database.scalar(select(User.id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "setup_complete", "message": "Initial setup is already complete."},
        )

    now = utc_now()
    user = User(
        id=1,
        username=payload.username,
        password_hash=passwords.hash(payload.password),
        password_changed_at=now,
    )
    database.add(user)

    try:
        await database.flush()
        _, token = sessions.create(database, user.id)
        await database.commit()
    except IntegrityError as error:
        await database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "setup_complete", "message": "Initial setup is already complete."},
        ) from error

    await database.refresh(user)
    set_session_cookie(response, token)
    return AuthUserResponse(username=user.username, created_at=user.created_at)


@router.post("/login", response_model=AuthUserResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    database: AsyncSession = Depends(get_session),
    passwords: PasswordService = Depends(get_password_service),
    sessions: SessionService = Depends(get_session_service),
    limiter: LoginRateLimiter = Depends(get_login_rate_limiter),
) -> AuthUserResponse:
    key = client_key(request)
    retry_after = await limiter.retry_after(key)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "too_many_attempts",
                "message": "Too many login attempts. Try again later.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    user = await database.scalar(select(User).where(User.id == 1))
    valid = passwords.verify_credentials(
        stored_username=user.username if user else None,
        expected_username=payload.username,
        password_hash=user.password_hash if user else None,
        password=payload.password,
    )
    if not valid:
        await limiter.record_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Invalid username or password."},
        )

    await limiter.reset(key)
    if passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash(payload.password)
        user.password_changed_at = utc_now()

    _, token = sessions.create(database, user.id)
    await database.commit()
    await database.refresh(user)
    set_session_cookie(response, token)
    return AuthUserResponse(username=user.username, created_at=user.created_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    database: AsyncSession = Depends(get_session),
    context: AuthContext | None = Depends(get_optional_auth),
) -> Response:
    if context is not None:
        context.session.revoked_at = utc_now()
        await database.commit()
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthUserResponse)
async def current_user(context: AuthContext = Depends(require_auth)) -> AuthUserResponse:
    return AuthUserResponse(username=context.user.username, created_at=context.user.created_at)


@router.put("/password", response_model=AuthUserResponse)
async def change_password(
    payload: PasswordChangeRequest,
    response: Response,
    context: AuthContext = Depends(require_auth),
    database: AsyncSession = Depends(get_session),
    passwords: PasswordService = Depends(get_password_service),
    sessions: SessionService = Depends(get_session_service),
) -> AuthUserResponse:
    if not passwords.verify(context.user.password_hash, payload.current_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Current password is incorrect."},
        )

    now = utc_now()
    context.user.password_hash = passwords.hash(payload.new_password)
    context.user.password_changed_at = now
    await database.execute(
        update(AuthSession)
        .where(AuthSession.user_id == context.user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    _, token = sessions.create(database, context.user.id)
    await database.commit()
    await database.refresh(context.user)
    set_session_cookie(response, token)
    return AuthUserResponse(username=context.user.username, created_at=context.user.created_at)


@router.delete("/sessions", response_model=SessionRevocationResponse)
async def revoke_other_sessions(
    context: AuthContext = Depends(require_auth),
    database: AsyncSession = Depends(get_session),
) -> SessionRevocationResponse:
    result = await database.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == context.user.id,
            AuthSession.id != context.session.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    await database.commit()
    return SessionRevocationResponse(revoked_sessions=result.rowcount or 0)
