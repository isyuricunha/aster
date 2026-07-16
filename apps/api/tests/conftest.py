import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ASTER_ENCRYPTION_KEY", "tests-only-encryption-key-with-32-characters")
os.environ.setdefault("ASTER_CORS_ORIGINS", "http://testserver")
os.environ.setdefault("ASTER_SESSION_SECURE", "false")

from app.auth_dependencies import (  # noqa: E402
    get_login_rate_limiter,
    get_password_service,
)
from app.auth_service import PasswordService  # noqa: E402
from app.db import Base, get_session  # noqa: E402
from app.dependencies import get_openai_client  # noqa: E402
from app.main import app  # noqa: E402


class FakeOpenAICompatibleClient:
    def __init__(self) -> None:
        self.models = ["alpha-model", "beta-model"]
        self.error = None
        self.received_api_key: str | None = None
        self.chat_chunks = ["Hello", " from Aster"]
        self.chat_error = None
        self.received_chat_api_key: str | None = None
        self.received_chat_model: str | None = None
        self.received_chat_messages: list[dict[str, str]] = []

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]:
        self.received_api_key = api_key
        if self.error is not None:
            raise self.error
        return self.models

    async def stream_chat_completion(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model_id: str,
        messages: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]:
        self.received_chat_api_key = api_key
        self.received_chat_model = model_id
        self.received_chat_messages = list(messages)
        if self.chat_error is not None:
            raise self.chat_error
        for chunk in self.chat_chunks:
            yield chunk


TestClientBundle = tuple[
    AsyncClient,
    FakeOpenAICompatibleClient,
    async_sessionmaker[AsyncSession],
]


@asynccontextmanager
async def build_test_client() -> AsyncIterator[TestClientBundle]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    fake_client = FakeOpenAICompatibleClient()
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_openai_client] = lambda: fake_client
    app.dependency_overrides[get_password_service] = lambda: PasswordService(
        memory_cost=1024,
        time_cost=1,
        parallelism=1,
    )
    limiter = get_login_rate_limiter()
    await limiter.clear()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client, fake_client, session_factory
    finally:
        app.dependency_overrides.clear()
        await limiter.clear()
        await engine.dispose()


@pytest_asyncio.fixture
async def unauthenticated_api_client() -> AsyncIterator[TestClientBundle]:
    async with build_test_client() as bundle:
        yield bundle


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[TestClientBundle]:
    async with build_test_client() as bundle:
        client, _, _ = bundle
        response = await client.post(
            "/api/auth/setup",
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        assert response.status_code == 201
        yield bundle
