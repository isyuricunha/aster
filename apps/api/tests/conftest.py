import json
import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENVIRONMENT", "test")
os.environ.setdefault("ASTER_ENCRYPTION_KEY", "tests-only-encryption-key-with-32-characters")
os.environ.setdefault("ASTER_CORS_ORIGINS", "http://testserver")
os.environ.setdefault("ASTER_SESSION_SECURE", "false")

from app.auth_dependencies import (  # noqa: E402
    get_login_rate_limiter,
    get_password_service,
)
from app.auth_service import PasswordService  # noqa: E402
from app.db import Base, get_session  # noqa: E402
from app.dependencies import get_mcp_client, get_openai_client  # noqa: E402
from app.main import app  # noqa: E402
from app.mcp_client import (  # noqa: E402
    McpConnectionConfig,
    McpToolDefinition,
    McpToolResult,
)
from app.openai_compatible import ChatCompletionDelta  # noqa: E402


class FakeMcpClient:
    def __init__(self) -> None:
        self.tools = [
            McpToolDefinition(
                name="echo",
                description="Return the provided value.",
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
            )
        ]
        self.list_error: Exception | None = None
        self.call_error: Exception | None = None
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.result: McpToolResult | None = None

    async def list_tools(self, config: McpConnectionConfig) -> list[McpToolDefinition]:
        if self.list_error is not None:
            raise self.list_error
        return self.tools

    async def call_tool(
        self,
        config: McpConnectionConfig,
        *,
        name: str,
        arguments: dict[str, object],
    ) -> McpToolResult:
        self.calls.append((name, arguments))
        if self.call_error is not None:
            raise self.call_error
        if self.result is not None:
            return self.result
        return McpToolResult(
            content=json.dumps({"name": name, "arguments": arguments}, sort_keys=True),
            is_error=False,
        )


class FakeOpenAICompatibleClient:
    def __init__(self) -> None:
        self.models = ["alpha-model", "beta-model"]
        self.error = None
        self.received_api_key: str | None = None
        self.chat_chunks = ["Hello", " from Aster"]
        self.chat_error = None
        self.chat_chunks_by_model: dict[str, list[str]] = {}
        self.chat_errors_by_model: dict[str, Exception] = {}
        self.chat_errors_after_chunks_by_model: dict[str, Exception] = {}
        self.chat_event_rounds: list[list[ChatCompletionDelta]] = []
        self.received_chat_api_key: str | None = None
        self.received_chat_model: str | None = None
        self.received_chat_messages: list[dict[str, object]] = []
        self.received_chat_options: dict[str, object] = {}
        self.received_chat_tools: list[dict[str, object]] = []
        self.chat_calls: list[str] = []
        self.mcp_client = FakeMcpClient()

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]:
        self.received_api_key = api_key
        if self.error is not None:
            raise self.error
        return self.models

    def _record_chat_call(
        self,
        *,
        api_key: str | None,
        model_id: str,
        messages: Sequence[dict[str, object]],
        tools: Sequence[dict[str, object]],
        temperature: float | None,
        top_p: float | None,
        max_output_tokens: int | None,
        token_parameter: str,
        reasoning_effort: str | None,
    ) -> None:
        self.received_chat_api_key = api_key
        self.received_chat_model = model_id
        self.received_chat_messages = list(messages)
        self.received_chat_tools = list(tools)
        self.received_chat_options = {
            "temperature": temperature,
            "top_p": top_p,
            "max_output_tokens": max_output_tokens,
            "token_parameter": token_parameter,
            "reasoning_effort": reasoning_effort,
        }
        self.chat_calls.append(model_id)

    async def stream_chat_completion(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model_id: str,
        messages: Sequence[dict[str, object]],
        temperature: float | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
        token_parameter: str = "max_tokens",
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[str]:
        self._record_chat_call(
            api_key=api_key,
            model_id=model_id,
            messages=messages,
            tools=(),
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,
            token_parameter=token_parameter,
            reasoning_effort=reasoning_effort,
        )
        model_error = self.chat_errors_by_model.get(model_id)
        if model_error is not None:
            raise model_error
        if self.chat_error is not None:
            raise self.chat_error
        for chunk in self.chat_chunks_by_model.get(model_id, self.chat_chunks):
            yield chunk
        trailing_error = self.chat_errors_after_chunks_by_model.get(model_id)
        if trailing_error is not None:
            raise trailing_error

    async def stream_chat_completion_events(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model_id: str,
        messages: Sequence[dict[str, object]],
        tools: Sequence[dict[str, object]] = (),
        temperature: float | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
        token_parameter: str = "max_tokens",
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[ChatCompletionDelta]:
        self._record_chat_call(
            api_key=api_key,
            model_id=model_id,
            messages=messages,
            tools=tools,
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,
            token_parameter=token_parameter,
            reasoning_effort=reasoning_effort,
        )
        model_error = self.chat_errors_by_model.get(model_id)
        if model_error is not None:
            raise model_error
        if self.chat_error is not None:
            raise self.chat_error
        events = (
            self.chat_event_rounds.pop(0)
            if self.chat_event_rounds
            else [
                ChatCompletionDelta(content=chunk)
                for chunk in self.chat_chunks_by_model.get(model_id, self.chat_chunks)
            ]
        )
        for item in events:
            yield item
        trailing_error = self.chat_errors_after_chunks_by_model.get(model_id)
        if trailing_error is not None:
            raise trailing_error


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
    app.dependency_overrides[get_mcp_client] = lambda: fake_client.mcp_client
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
