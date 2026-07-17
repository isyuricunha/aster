import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


class McpClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class McpConnectionConfig:
    transport: Literal["streamable_http", "stdio"]
    timeout_seconds: float
    url: str | None = None
    command: str | None = None
    arguments: tuple[str, ...] = ()
    headers: dict[str, str] | None = None
    environment: dict[str, str] | None = None
    stdio_enabled: bool = False


@dataclass(frozen=True, slots=True)
class McpToolDefinition:
    name: str
    description: str
    input_schema: dict[str, object]


@dataclass(frozen=True, slots=True)
class McpToolResult:
    content: str
    is_error: bool


class McpClient:
    @asynccontextmanager
    async def _session(self, config: McpConnectionConfig) -> AsyncIterator[ClientSession]:
        try:
            async with asyncio.timeout(config.timeout_seconds):
                if config.transport == "streamable_http":
                    if not config.url:
                        raise McpClientError(
                            "invalid_configuration",
                            "The MCP server does not have a Streamable HTTP URL.",
                        )
                    async with httpx.AsyncClient(
                        headers=config.headers,
                        timeout=config.timeout_seconds,
                        follow_redirects=False,
                    ) as http_client:
                        async with streamable_http_client(
                            config.url,
                            http_client=http_client,
                        ) as (read_stream, write_stream, _):
                            async with ClientSession(read_stream, write_stream) as session:
                                await session.initialize()
                                yield session
                    return

                if not config.stdio_enabled:
                    raise McpClientError(
                        "stdio_disabled",
                        "Stdio MCP servers are disabled by the Aster runtime configuration.",
                    )
                if not config.command:
                    raise McpClientError(
                        "invalid_configuration",
                        "The MCP server does not have a command.",
                    )
                parameters = StdioServerParameters(
                    command=config.command,
                    args=list(config.arguments),
                    env=config.environment,
                )
                async with stdio_client(parameters) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        yield session
        except McpClientError:
            raise
        except TimeoutError as error:
            raise McpClientError(
                "timeout",
                "The MCP server did not complete the request before the timeout.",
            ) from error
        except Exception as error:
            raise McpClientError(
                "connection_failed",
                "The MCP server could not be reached or completed an invalid protocol exchange.",
            ) from error

    async def list_tools(self, config: McpConnectionConfig) -> list[McpToolDefinition]:
        async with self._session(config) as session:
            try:
                response = await session.list_tools()
            except Exception as error:
                raise McpClientError(
                    "list_tools_failed",
                    "The MCP server could not list its tools.",
                ) from error

        definitions: list[McpToolDefinition] = []
        for tool in response.tools:
            schema = tool.inputSchema
            if not isinstance(schema, dict):
                schema = {"type": "object", "properties": {}}
            definitions.append(
                McpToolDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=schema,
                )
            )
        return definitions

    async def call_tool(
        self,
        config: McpConnectionConfig,
        *,
        name: str,
        arguments: dict[str, object],
    ) -> McpToolResult:
        async with self._session(config) as session:
            try:
                response = await session.call_tool(name, arguments=arguments)
            except Exception as error:
                raise McpClientError(
                    "tool_call_failed",
                    "The MCP tool call failed.",
                ) from error

        structured = getattr(response, "structuredContent", None)
        if structured is None:
            structured = getattr(response, "structured_content", None)
        if structured is not None:
            content = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
        else:
            blocks = [
                block.model_dump(mode="json", by_alias=True, exclude_none=True)
                for block in response.content
            ]
            if len(blocks) == 1 and blocks[0].get("type") == "text":
                content = str(blocks[0].get("text", ""))
            else:
                content = json.dumps(blocks, ensure_ascii=False, separators=(",", ":"))

        return McpToolResult(
            content=content,
            is_error=bool(getattr(response, "isError", False)),
        )
