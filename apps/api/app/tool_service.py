import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.mcp_client import McpClient, McpClientError, McpConnectionConfig, McpToolResult
from app.models import ConversationTool, McpServer, McpTool
from app.security import SecretCipher
from app.tool_schemas import McpServerResponse, McpToolResponse


@dataclass(frozen=True, slots=True)
class ToolRuntime:
    tool: McpTool
    server: McpServer
    connection: McpConnectionConfig

    @property
    def provider_definition(self) -> dict[str, object]:
        description = self.tool.description.strip()
        server_prefix = f"MCP server: {self.server.name}."
        return {
            "type": "function",
            "function": {
                "name": self.tool.public_name,
                "description": f"{server_prefix} {description}".strip(),
                "parameters": self.tool.input_schema,
            },
        }


def encrypt_secret_map(cipher: SecretCipher, values: dict[str, str]) -> str | None:
    if not values:
        return None
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return cipher.encrypt(payload)


def decrypt_secret_map(cipher: SecretCipher, value: str | None) -> dict[str, str]:
    if value is None:
        return {}
    decoded = json.loads(cipher.decrypt(value))
    if not isinstance(decoded, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in decoded.items()
    ):
        raise ValueError("Encrypted MCP credentials contain an invalid value")
    return decoded


def connection_config(
    server: McpServer,
    *,
    cipher: SecretCipher,
    settings: Settings,
) -> McpConnectionConfig:
    timeout = min(float(server.timeout_seconds), settings.aster_mcp_timeout_seconds)
    return McpConnectionConfig(
        transport=server.transport,
        timeout_seconds=timeout,
        url=server.url,
        command=server.command,
        arguments=tuple(server.arguments),
        headers=decrypt_secret_map(cipher, server.encrypted_headers),
        environment=decrypt_secret_map(cipher, server.encrypted_environment),
        stdio_enabled=settings.aster_mcp_stdio_enabled,
    )


def public_tool_name(server_id: UUID, tool_name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", tool_name).strip("_") or "tool"
    digest = hashlib.sha256(tool_name.encode("utf-8")).hexdigest()[:8]
    return f"mcp_{server_id.hex[:8]}_{normalized[:38]}_{digest}"[:64]


def tool_response(tool: McpTool, server_name: str) -> McpToolResponse:
    return McpToolResponse(
        id=tool.id,
        server_id=tool.server_id,
        server_name=server_name,
        name=tool.name,
        public_name=tool.public_name,
        description=tool.description,
        input_schema=tool.input_schema,
        enabled=tool.enabled,
        default_enabled=tool.default_enabled,
        requires_confirmation=tool.requires_confirmation,
        is_available=tool.is_available,
        last_seen_at=tool.last_seen_at,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


async def server_response(session: AsyncSession, server: McpServer) -> McpServerResponse:
    tool_count, available_tool_count = (
        await session.execute(
            select(
                func.count(McpTool.id),
                func.count(McpTool.id).filter(McpTool.is_available.is_(True)),
            ).where(McpTool.server_id == server.id)
        )
    ).one()
    return McpServerResponse(
        id=server.id,
        name=server.name,
        transport=server.transport,
        url=server.url,
        command=server.command,
        arguments=list(server.arguments),
        header_names=list(server.header_names),
        environment_names=list(server.environment_names),
        enabled=server.enabled,
        timeout_seconds=server.timeout_seconds,
        tool_count=tool_count,
        available_tool_count=available_tool_count,
        last_sync_status=server.last_sync_status,
        last_sync_at=server.last_sync_at,
        last_error=server.last_error,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


async def sync_server_tools(
    session: AsyncSession,
    *,
    server: McpServer,
    cipher: SecretCipher,
    settings: Settings,
    client: McpClient,
) -> tuple[int, datetime]:
    synchronized_at = datetime.now(UTC)
    try:
        definitions = await client.list_tools(
            connection_config(server, cipher=cipher, settings=settings)
        )
    except McpClientError as error:
        server.last_sync_status = "failed"
        server.last_sync_at = synchronized_at
        server.last_error = error.message[:500]
        await session.commit()
        raise

    existing = {
        tool.name: tool
        for tool in await session.scalars(select(McpTool).where(McpTool.server_id == server.id))
    }
    for tool in existing.values():
        tool.is_available = False

    for definition in definitions:
        tool = existing.get(definition.name)
        if tool is None:
            tool = McpTool(
                server_id=server.id,
                name=definition.name,
                public_name=public_tool_name(server.id, definition.name),
            )
            session.add(tool)
        tool.description = definition.description[:20_000]
        tool.input_schema = definition.input_schema
        tool.is_available = True
        tool.last_seen_at = synchronized_at

    server.last_sync_status = "succeeded"
    server.last_sync_at = synchronized_at
    server.last_error = None
    await session.commit()
    return len(definitions), synchronized_at


async def copy_default_tools_to_conversation(
    session: AsyncSession,
    *,
    conversation_id: UUID,
) -> None:
    tool_ids = list(
        await session.scalars(
            select(McpTool.id).where(
                McpTool.enabled.is_(True),
                McpTool.default_enabled.is_(True),
                McpTool.is_available.is_(True),
            )
        )
    )
    session.add_all(
        [ConversationTool(conversation_id=conversation_id, tool_id=tool_id) for tool_id in tool_ids]
    )


async def replace_conversation_tools(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    tool_ids: list[UUID],
) -> list[McpToolResponse]:
    rows = (
        await session.execute(
            select(McpTool, McpServer)
            .join(McpServer, McpServer.id == McpTool.server_id)
            .where(
                McpTool.id.in_(tool_ids),
                McpTool.enabled.is_(True),
                McpTool.is_available.is_(True),
                McpServer.enabled.is_(True),
            )
        )
    ).all()
    if len(rows) != len(tool_ids):
        raise ValueError("Every selected tool must be enabled and available")

    await session.execute(
        delete(ConversationTool).where(ConversationTool.conversation_id == conversation_id)
    )
    session.add_all(
        [ConversationTool(conversation_id=conversation_id, tool_id=tool_id) for tool_id in tool_ids]
    )
    await session.commit()
    by_id = {tool.id: (tool, server) for tool, server in rows}
    return [tool_response(*by_id[tool_id]) for tool_id in tool_ids]


async def conversation_tool_responses(
    session: AsyncSession,
    *,
    conversation_id: UUID,
) -> list[McpToolResponse]:
    rows = (
        await session.execute(
            select(McpTool, McpServer)
            .join(ConversationTool, ConversationTool.tool_id == McpTool.id)
            .join(McpServer, McpServer.id == McpTool.server_id)
            .where(ConversationTool.conversation_id == conversation_id)
            .order_by(McpServer.name.asc(), McpTool.name.asc())
        )
    ).all()
    return [tool_response(tool, server.name) for tool, server in rows]


async def resolve_conversation_tool_runtimes(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    cipher: SecretCipher,
    settings: Settings,
) -> list[ToolRuntime]:
    rows = (
        await session.execute(
            select(McpTool, McpServer)
            .join(ConversationTool, ConversationTool.tool_id == McpTool.id)
            .join(McpServer, McpServer.id == McpTool.server_id)
            .where(
                ConversationTool.conversation_id == conversation_id,
                McpTool.enabled.is_(True),
                McpTool.is_available.is_(True),
                McpServer.enabled.is_(True),
            )
            .order_by(McpServer.name.asc(), McpTool.name.asc())
        )
    ).all()
    return [
        ToolRuntime(
            tool=tool,
            server=server,
            connection=connection_config(server, cipher=cipher, settings=settings),
        )
        for tool, server in rows
    ]


async def execute_runtime_tool(
    client: McpClient,
    runtime: ToolRuntime,
    *,
    arguments: dict[str, object],
    result_limit: int,
) -> McpToolResult:
    result = await client.call_tool(
        runtime.connection,
        name=runtime.tool.name,
        arguments=arguments,
    )
    if len(result.content) <= result_limit:
        return result
    suffix = "\n\n[Tool result truncated by Aster]"
    return McpToolResult(
        content=f"{result.content[: max(0, result_limit - len(suffix))]}{suffix}",
        is_error=result.is_error,
    )
