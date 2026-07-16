import os
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ASTER_ENCRYPTION_KEY", "tests-only-encryption-key-with-32-characters")

from app.db import Base, get_session  # noqa: E402
from app.dependencies import get_openai_client  # noqa: E402
from app.main import app  # noqa: E402


class FakeOpenAICompatibleClient:
    def __init__(self) -> None:
        self.models = ["alpha-model", "beta-model"]
        self.error = None
        self.received_api_key: str | None = None

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]:
        self.received_api_key = api_key
        if self.error is not None:
            raise self.error
        return self.models


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[
    tuple[AsyncClient, FakeOpenAICompatibleClient, async_sessionmaker[AsyncSession]]
]:
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

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client, fake_client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()
