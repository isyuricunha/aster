from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_generation import ensure_no_active_generation, get_conversation
from app.chat_tool_responses import execution_response
from app.config import settings
from app.db import get_session
from app.dependencies import get_mcp_client, get_openai_client, get_secret_cipher
from app.mcp_client import McpClient, McpClientError
from app.models import ConversationTool, McpServer, McpTool, ToolExecution
from app.openai_compatible import OpenAICompatibleClient
from app.security import SecretCipher
from app.tool_decision_runtime import tool_decision_registry
from app.tool_generation import continue_tool_execution
from app.tool_guards import ensure_no_pending_tool_confirmation
from app.tool_schemas import (
    ConversationToolSettingsResponse,
    ConversationToolSettingsUpdate,
    McpConnectionTestResponse,
    McpServerCreate,
    McpServerResponse,
    McpServerUpdate,
    McpSyncResponse,
    McpToolResponse,
    McpToolUpdate,
    ToolExecutionResponse,
)
from app.tool_service import (
    connection_config,
    conversation_tool_responses,
    encrypt_secret_map,
    replace_conversation_tools,
    server_response,
    sync_server_tools,
    tool_response,
)

router = APIRouter(prefix="/api", tags=["tools"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]
McpClientDep = Annotated[McpClient, Depends(get_mcp_client)]
OpenAIClientDep = Annotated[OpenAICompatibleClient, Depends(get_openai_client)]


async def _get_server(session: AsyncSession, server_id: UUID) -> McpServer:
    server = await session.get(McpServer, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


async def _get_tool(session: AsyncSession, tool_id: UUID) -> McpTool:
    tool = await session.get(McpTool, tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="MCP tool not found")
    return tool


def _raise_mcp_error(error: McpClientError) -> None:
    status_code = 422 if error.code in {"invalid_configuration", "stdio_disabled"} else 502
    raise HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


async def _name_is_taken(
    session: AsyncSession,
    *,
    name: str,
    exclude_id: UUID | None = None,
) -> bool:
    statement = select(McpServer.id).where(McpServer.name == name)
    if exclude_id is not None:
        statement = statement.where(McpServer.id != exclude_id)
    return await session.scalar(statement) is not None


@router.get("/mcp-servers", response_model=list[McpServerResponse])
async def list_mcp_servers(session: SessionDep) -> list[McpServerResponse]:
    servers = list(await session.scalars(select(McpServer).order_by(McpServer.name.asc())))
    return [await server_response(session, server) for server in servers]


@router.post(
    "/mcp-servers",
    response_model=McpServerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mcp_server(
    payload: McpServerCreate,
    session: SessionDep,
    cipher: CipherDep,
) -> McpServerResponse:
    if await _name_is_taken(session, name=payload.name):
        raise HTTPException(status_code=409, detail="An MCP server with this name already exists")
    server = McpServer(
        name=payload.name,
        transport=payload.transport,
        url=payload.url,
        command=payload.command,
        arguments=payload.arguments,
        encrypted_headers=encrypt_secret_map(cipher, payload.headers),
        header_names=sorted(payload.headers),
        encrypted_environment=encrypt_secret_map(cipher, payload.environment),
        environment_names=sorted(payload.environment),
        enabled=payload.enabled,
        timeout_seconds=payload.timeout_seconds,
    )
    session.add(server)
    await session.commit()
    await session.refresh(server)
    return await server_response(session, server)


@router.get("/mcp-servers/{server_id}", response_model=McpServerResponse)
async def read_mcp_server(server_id: UUID, session: SessionDep) -> McpServerResponse:
    return await server_response(session, await _get_server(session, server_id))


@router.put("/mcp-servers/{server_id}", response_model=McpServerResponse)
async def update_mcp_server(
    server_id: UUID,
    payload: McpServerUpdate,
    session: SessionDep,
    cipher: CipherDep,
) -> McpServerResponse:
    server = await _get_server(session, server_id)
    if await _name_is_taken(session, name=payload.name, exclude_id=server.id):
        raise HTTPException(status_code=409, detail="An MCP server with this name already exists")

    previous_transport = server.transport
    server.name = payload.name
    server.transport = payload.transport
    server.url = payload.url
    server.command = payload.command
    server.arguments = payload.arguments
    server.enabled = payload.enabled
    server.timeout_seconds = payload.timeout_seconds

    transport_changed = previous_transport != payload.transport
    if payload.transport == "streamable_http":
        if payload.headers or not payload.preserve_secrets or transport_changed:
            server.encrypted_headers = encrypt_secret_map(cipher, payload.headers)
            server.header_names = sorted(payload.headers)
        if transport_changed:
            server.encrypted_environment = None
            server.environment_names = []
    else:
        if payload.environment or not payload.preserve_secrets or transport_changed:
            server.encrypted_environment = encrypt_secret_map(cipher, payload.environment)
            server.environment_names = sorted(payload.environment)
        if transport_changed:
            server.encrypted_headers = None
            server.header_names = []

    server.last_sync_status = None
    server.last_error = None
    await session.commit()
    await session.refresh(server)
    return await server_response(session, server)


@router.delete("/mcp-servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(server_id: UUID, session: SessionDep) -> Response:
    server = await _get_server(session, server_id)
    await session.delete(server)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mcp-servers/{server_id}/test", response_model=McpConnectionTestResponse)
async def test_mcp_server(
    server_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
    client: McpClientDep,
) -> McpConnectionTestResponse:
    server = await _get_server(session, server_id)
    try:
        tools = await client.list_tools(
            connection_config(server, cipher=cipher, settings=settings)
        )
    except McpClientError as error:
        _raise_mcp_error(error)
    return McpConnectionTestResponse(
        tools_found=len(tools),
        message=f"The MCP server exposed {len(tools)} tool(s).",
    )


@router.post("/mcp-servers/{server_id}/sync", response_model=McpSyncResponse)
async def sync_mcp_server(
    server_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
    client: McpClientDep,
) -> McpSyncResponse:
    server = await _get_server(session, server_id)
    try:
        tools_found, synchronized_at = await sync_server_tools(
            session,
            server=server,
            cipher=cipher,
            settings=settings,
            client=client,
        )
    except McpClientError as error:
        _raise_mcp_error(error)
    return McpSyncResponse(tools_found=tools_found, synchronized_at=synchronized_at)


@router.get("/mcp-tools", response_model=list[McpToolResponse])
async def list_mcp_tools(session: SessionDep) -> list[McpToolResponse]:
    rows = (
        await session.execute(
            select(McpTool, McpServer)
            .join(McpServer, McpServer.id == McpTool.server_id)
            .order_by(McpServer.name.asc(), McpTool.name.asc())
        )
    ).all()
    return [tool_response(tool, server.name) for tool, server in rows]


@router.put("/mcp-tools/{tool_id}", response_model=McpToolResponse)
async def update_mcp_tool(
    tool_id: UUID,
    payload: McpToolUpdate,
    session: SessionDep,
) -> McpToolResponse:
    tool = await _get_tool(session, tool_id)
    if payload.enabled and not tool.is_available:
        raise HTTPException(status_code=422, detail="An unavailable tool cannot be enabled")
    tool.enabled = payload.enabled
    tool.default_enabled = payload.default_enabled
    tool.requires_confirmation = payload.requires_confirmation
    if not tool.enabled:
        tool.default_enabled = False
        await session.execute(delete(ConversationTool).where(ConversationTool.tool_id == tool.id))
    await session.commit()
    await session.refresh(tool)
    server = await _get_server(session, tool.server_id)
    return tool_response(tool, server.name)


@router.get(
    "/conversations/{conversation_id}/tools",
    response_model=ConversationToolSettingsResponse,
)
async def read_conversation_tools(
    conversation_id: UUID,
    session: SessionDep,
) -> ConversationToolSettingsResponse:
    await get_conversation(session, conversation_id)
    tools = await conversation_tool_responses(session, conversation_id=conversation_id)
    return ConversationToolSettingsResponse(conversation_id=conversation_id, tools=tools)


@router.put(
    "/conversations/{conversation_id}/tools",
    response_model=ConversationToolSettingsResponse,
)
async def update_conversation_tools(
    conversation_id: UUID,
    payload: ConversationToolSettingsUpdate,
    session: SessionDep,
) -> ConversationToolSettingsResponse:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    await ensure_no_active_generation(session, conversation.id)
    await ensure_no_pending_tool_confirmation(session, conversation.id)
    try:
        tools = await replace_conversation_tools(
            session,
            conversation_id=conversation.id,
            tool_ids=payload.tool_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return ConversationToolSettingsResponse(conversation_id=conversation.id, tools=tools)


@router.get(
    "/conversations/{conversation_id}/tool-executions",
    response_model=list[ToolExecutionResponse],
)
async def list_tool_executions(
    conversation_id: UUID,
    session: SessionDep,
) -> list[ToolExecutionResponse]:
    await get_conversation(session, conversation_id)
    executions = list(
        await session.scalars(
            select(ToolExecution)
            .where(ToolExecution.conversation_id == conversation_id)
            .order_by(ToolExecution.created_at.asc())
        )
    )
    return [execution_response(execution) for execution in executions]


async def _continue_tool_decision(
    *,
    execution_id: UUID,
    approved: bool,
    session: AsyncSession,
    cipher: SecretCipher,
    openai_client: OpenAICompatibleClient,
    mcp_client: McpClient,
) -> StreamingResponse:
    execution = await session.get(ToolExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Tool execution not found")

    lease = await tool_decision_registry.acquire(execution.conversation_id)
    try:
        response = await continue_tool_execution(
            execution_id=execution_id,
            approved=approved,
            session=session,
            cipher=cipher,
            client=openai_client,
            mcp_client=mcp_client,
        )
    except BaseException:
        await lease.release()
        raise

    async def body() -> AsyncIterator[bytes | str]:
        try:
            async for chunk in response.body_iterator:
                yield chunk
        finally:
            await lease.release()

    headers = {
        name: value
        for name, value in response.headers.items()
        if name.lower() not in {"content-length", "content-type"}
    }
    return StreamingResponse(
        body(),
        status_code=response.status_code,
        media_type=response.media_type,
        headers=headers,
    )


@router.post("/tool-executions/{execution_id}/approve")
async def approve_tool_execution(
    execution_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
    openai_client: OpenAIClientDep,
    mcp_client: McpClientDep,
) -> StreamingResponse:
    return await _continue_tool_decision(
        execution_id=execution_id,
        approved=True,
        session=session,
        cipher=cipher,
        openai_client=openai_client,
        mcp_client=mcp_client,
    )


@router.post("/tool-executions/{execution_id}/deny")
async def deny_tool_execution(
    execution_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
    openai_client: OpenAIClientDep,
    mcp_client: McpClientDep,
) -> StreamingResponse:
    return await _continue_tool_decision(
        execution_id=execution_id,
        approved=False,
        session=session,
        cipher=cipher,
        openai_client=openai_client,
        mcp_client=mcp_client,
    )
