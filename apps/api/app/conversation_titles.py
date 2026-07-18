import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_openai_client, get_secret_cipher
from app.model_routing import resolve_utility_target
from app.models import ChatMessage, Conversation
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.security import SecretCipher

logger = logging.getLogger(__name__)

_TITLE_PATH = re.compile(
    r"^/api/conversations/(?P<conversation_id>[0-9a-fA-F-]{36})/messages/stream$"
)
_TITLE_PREFIX = re.compile(r"^(?:title|t[ií]tulo)\s*[:\-]\s*", re.IGNORECASE)
_MAX_SOURCE_CHARACTERS = 12_000
_MAX_RAW_TITLE_CHARACTERS = 500
_MAX_TITLE_CHARACTERS = 80

SessionProvider = Callable[[], AsyncIterator[AsyncSession]]


def fallback_title(content: str) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= 60:
        return normalized
    return f"{normalized[:57].rstrip()}..."


def normalize_generated_title(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        last_fence = text.rfind("```")
        if first_newline >= 0 and last_fence > first_newline:
            text = text[first_newline + 1 : last_fence].strip()
    line = next((item.strip() for item in text.splitlines() if item.strip()), "")
    line = _TITLE_PREFIX.sub("", line).strip().strip('"\'`“”‘’')
    line = " ".join(line.split()).strip(" .,:;!?—–-")
    if not line:
        raise ValueError("The Utility model returned an empty conversation title")
    if len(line) > _MAX_TITLE_CHARACTERS:
        line = line[: _MAX_TITLE_CHARACTERS - 3].rstrip() + "..."
    return line


@asynccontextmanager
async def _session_scope(provider: SessionProvider) -> AsyncIterator[AsyncSession]:
    generator = provider()
    session = await anext(generator)
    try:
        yield session
    finally:
        await generator.aclose()


async def generate_initial_conversation_title(
    *,
    conversation_id: UUID,
    session_provider: SessionProvider,
    client: OpenAICompatibleClient,
    cipher: SecretCipher,
) -> None:
    async with _session_scope(session_provider) as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            return
        user_messages = list(
            await session.scalars(
                select(ChatMessage)
                .where(
                    ChatMessage.conversation_id == conversation_id,
                    ChatMessage.role == "user",
                )
                .order_by(ChatMessage.position.asc())
            )
        )
        if len(user_messages) != 1:
            return
        content = user_messages[0].content
        expected_title = fallback_title(content)
        if conversation.title != expected_title:
            return
        target = await resolve_utility_target(
            session,
            cipher,
            purpose="conversation title",
            max_output_tokens=80,
            temperature=0.2,
        )

    prompt = (
        "Create a concise title for the conversation started by the user message below. "
        "Use the same language as the user. Return only the title, with no quotes, prefix, "
        "Markdown, explanation, or ending punctuation. Prefer 2 to 8 words and never exceed "
        "80 characters.\n\nUSER MESSAGE:\n"
        f"{content[:_MAX_SOURCE_CHARACTERS]}"
    )
    chunks: list[str] = []
    output_characters = 0
    parameters = target.parameters
    async for chunk in client.stream_chat_completion(
        base_url=target.base_url,
        api_key=target.api_key,
        model_id=target.provider_model_id,
        messages=[
            {
                "role": "developer",
                "content": (
                    "You generate short, accurate conversation titles. "
                    "Output only the title."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=parameters.temperature,
        top_p=parameters.top_p,
        max_output_tokens=parameters.max_output_tokens,
        token_parameter=parameters.token_parameter,
        reasoning_effort=parameters.reasoning_effort,
    ):
        chunks.append(chunk)
        output_characters += len(chunk)
        if output_characters > _MAX_RAW_TITLE_CHARACTERS:
            raise ValueError("The Utility model returned too much title text")
    generated_title = normalize_generated_title("".join(chunks))

    async with _session_scope(session_provider) as session:
        conversation = await session.get(Conversation, conversation_id, with_for_update=True)
        if conversation is None or conversation.title != expected_title:
            return
        current_user_count = int(
            await session.scalar(
                select(func.count(ChatMessage.id)).where(
                    ChatMessage.conversation_id == conversation_id,
                    ChatMessage.role == "user",
                )
            )
            or 0
        )
        if current_user_count != 1:
            return
        conversation.title = generated_title
        await session.commit()


def _provider(scope: dict[str, Any], provider: Callable[..., Any]) -> Callable[..., Any]:
    application = scope.get("app")
    overrides = getattr(application, "dependency_overrides", {})
    return overrides.get(provider, provider)


def _dependency(scope: dict[str, Any], provider: Callable[[], Any]) -> Any:
    return _provider(scope, provider)()


class ConversationTitleMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        match = (
            _TITLE_PATH.fullmatch(str(scope.get("path", "")))
            if scope.get("type") == "http" and scope.get("method") == "POST"
            else None
        )
        if match is None:
            await self.app(scope, receive, send)
            return

        attempted = False

        async def send_with_title(message: dict[str, Any]) -> None:
            nonlocal attempted
            if (
                not attempted
                and message.get("type") == "http.response.start"
                and 200 <= int(message.get("status", 500)) < 300
            ):
                attempted = True
                try:
                    await generate_initial_conversation_title(
                        conversation_id=UUID(match.group("conversation_id")),
                        session_provider=_provider(scope, get_session),
                        client=_dependency(scope, get_openai_client),
                        cipher=_dependency(scope, get_secret_cipher),
                    )
                except (HTTPException, ModelEndpointError, ValueError, OSError) as error:
                    logger.info("Conversation title generation fell back to local text: %s", error)
                except Exception:
                    logger.exception("Unexpected conversation title generation failure")
            await send(message)

        await self.app(scope, receive, send_with_title)
