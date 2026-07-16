import asyncio
import hashlib
import secrets
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AuthSession, User


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PasswordService:
    def __init__(
        self,
        *,
        memory_cost: int = 19_456,
        time_cost: int = 2,
        parallelism: int = 1,
    ) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self._dummy_hash = self._hasher.hash("aster-dummy-password-verification")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False

    def verify_credentials(
        self,
        *,
        stored_username: str | None,
        expected_username: str,
        password_hash: str | None,
        password: str,
    ) -> bool:
        username_matches = (
            stored_username is not None
            and secrets.compare_digest(
                stored_username.encode("utf-8"),
                expected_username.encode("utf-8"),
            )
        )
        selected_hash = password_hash if username_matches and password_hash else self._dummy_hash
        password_matches = self.verify(selected_hash, password)
        return username_matches and password_matches

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHashError:
            return True


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession


class SessionService:
    def create(self, database: AsyncSession, user_id: int) -> tuple[AuthSession, str]:
        now = utc_now()
        token = secrets.token_urlsafe(32)
        auth_session = AuthSession(
            user_id=user_id,
            token_hash=token_digest(token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=settings.aster_session_absolute_days),
        )
        database.add(auth_session)
        return auth_session, token

    async def resolve(self, database: AsyncSession, token: str | None) -> AuthContext | None:
        if not token:
            return None

        now = utc_now()
        idle_cutoff = now - timedelta(hours=settings.aster_session_idle_hours)
        result = await database.execute(
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(
                AuthSession.token_hash == token_digest(token),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                AuthSession.last_seen_at > idle_cutoff,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None

        auth_session, user = row
        touch_cutoff = now - timedelta(seconds=settings.aster_session_touch_seconds)
        if ensure_utc(auth_session.last_seen_at) <= touch_cutoff:
            auth_session.last_seen_at = now
            await database.commit()

        return AuthContext(user=user, session=auth_session)


class LoginRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def retry_after(self, key: str) -> int | None:
        now = utc_now()
        window = timedelta(seconds=settings.aster_login_window_seconds)
        async with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= now - window:
                attempts.popleft()
            if len(attempts) < settings.aster_login_attempts:
                return None
            remaining = int((attempts[0] + window - now).total_seconds())
            return max(remaining, 1)

    async def record_failure(self, key: str) -> None:
        async with self._lock:
            self._attempts[key].append(utc_now())

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._attempts.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._attempts.clear()


def session_cookie_options() -> dict[str, object]:
    return {
        "key": settings.aster_session_cookie_name,
        "httponly": True,
        "secure": settings.aster_session_secure,
        "samesite": "lax",
        "path": "/",
        "max_age": settings.aster_session_absolute_days * 24 * 60 * 60,
    }
