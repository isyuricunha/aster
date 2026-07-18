import json
import logging
import re
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation_title_models import ConversationTitleState
from app.db import get_session
from app.dependencies import get_openai_client, get_secret_cipher
from app.model_routing import resolve_utility_target
from app.models import ChatMessage, Conversation
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.security import SecretCipher

logger = logging.getLogger(__name__)

_GENERATE_PATH = re.compile(
    r"^/api/conversations/(?P<conversation_id>[0-9a-fA-F-]{36})/messages/"
    r"(?:stream|[0-9a-fA-F-]{36}/edit-and-resend)$"
)
_CONVERSATION_PATH = re.compile(
    r"^/api/conversations/(?P<conversation_id>[0-9a-fA-F-]{36})$"
)
_TITLE_PREFIX = re.compile(r"^(?:title|t[ií]tulo)\s*[:\-]\s*", re.IGNORECASE)
_MAX_SOURCE_CHARACTERS = 12_000
_MAX_RAW_TITLE_CHARACTERS = 500
_MAX_TITLE_CHARACTERS = 80

SessionProvider = Callable[[], AsyncIterator[AsyncSession]]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


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


async def generate_conversation_title(
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
        local_title = fallback_title(content)
        state = await session.get(ConversationTitleState, conversation_id)
        if state is None and conversation.title != local_title:
            return
        if conversation.title != local_title:
            conversation.title = local_title
            await session.commit()
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
        if conversation is None or conversation.title != local_title:
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
        state = await session.get(ConversationTitleState, conversation_id)
        if state is None:
            session.add(ConversationTitleState(conversation_id=conversation_id))
        await session.commit()


async def mark_title_manual(
    *,
    conversation_id: UUID,
    session_provider: SessionProvider,
) -> None:
    async with _session_scope(session_provider) as session:
        state = await session.get(ConversationTitleState, conversation_id)
        if state is None:
            return
        await session.delete(state)
        await session.commit()


def _provider(scope: dict[str, Any], provider: Callable[..., Any]) -> Callable[..., Any]:
    application = scope.get("app")
    overrides = getattr(application, "dependency_overrides", {})
    return overrides.get(provider, provider)


def _dependency(scope: dict[str, Any], provider: Callable[[], Any]) -> Any:
    return _provider(scope, provider)()


async def _capture_request(receive: Receive) -> tuple[bytes, Receive]:
    messages: deque[dict[str, Any]] = deque()
    body = bytearray()
    while True:
        message = await receive()
        messages.append(message)
        if message.get("type") != "http.request":
            break
        body.extend(message.get("body", b""))
        if not message.get("more_body", False):
            break

    async def replay() -> dict[str, Any]:
        if messages:
            return messages.popleft()
        return {"type": "http.request", "body": b"", "more_body": False}

    return bytes(body), replay


class ConversationTitleMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
        path = str(scope.get("path", ""))
        method = scope.get("method")
        generate_match = (
            _GENERATE_PATH.fullmatch(path)
            if scope.get("type") == "http" and method == "POST"
            else None
        )
        conversation_match = (
            _CONVERSATION_PATH.fullmatch(path)
            if scope.get("type") == "http" and method == "PATCH"
            else None
        )
        manual_title = False
        if conversation_match is not None:
            body, receive = await _capture_request(receive)
            try:
                payload = json.loads(body) if body else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
            manual_title = isinstance(payload, dict) and "title" in payload

        if generate_match is None and not manual_title:
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
                    if generate_match is not None:
                        await generate_conversation_title(
                            conversation_id=UUID(generate_match.group("conversation_id")),
                            session_provider=_provider(scope, get_session),
                            client=_dependency(scope, get_openai_client),
                            cipher=_dependency(scope, get_secret_cipher),
                        )
                    elif conversation_match is not None:
                        await mark_title_manual(
                            conversation_id=UUID(conversation_match.group("conversation_id")),
                            session_provider=_provider(scope, get_session),
                        )
                except (HTTPException, ModelEndpointError, ValueError, OSError) as error:
                    logger.info("Conversation title handling used its safe fallback: %s", error)
                except Exception:
                    logger.exception("Unexpected conversation title handling failure")
            await send(message)

        await self.app(scope, receive, send_with_title)
