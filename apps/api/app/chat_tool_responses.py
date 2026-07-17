from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_generation import conversation_persona_response
from app.chat_tool_schemas import ToolAwareChatMessageResponse, ToolAwareConversationResponse
from app.models import ChatMessage, Conversation, ToolExecution
from app.tool_schemas import ToolExecutionResponse


def message_response(message: ChatMessage) -> ToolAwareChatMessageResponse:
    return ToolAwareChatMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        status=message.status,
        error_message=message.error_message,
        model_id=message.model_id,
        tool_calls=message.tool_calls,
        tool_call_id=message.tool_call_id,
        tool_name=message.tool_name,
        position=message.position,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _loaded_execution_updated_at(execution: ToolExecution) -> datetime:
    value = execution.__dict__.get("updated_at")
    if isinstance(value, datetime):
        return value
    return execution.finished_at or execution.created_at


def execution_response(execution: ToolExecution) -> ToolExecutionResponse:
    return ToolExecutionResponse(
        id=execution.id,
        conversation_id=execution.conversation_id,
        assistant_message_id=execution.assistant_message_id,
        tool_message_id=execution.tool_message_id,
        tool_id=execution.tool_id,
        tool_call_id=execution.tool_call_id,
        tool_name=execution.tool_name,
        arguments=execution.arguments,
        status=execution.status,
        result=execution.result,
        error_message=execution.error_message,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        created_at=execution.created_at,
        updated_at=_loaded_execution_updated_at(execution),
    )


async def conversation_response(
    session: AsyncSession,
    conversation: Conversation,
) -> ToolAwareConversationResponse:
    messages = list(
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.position.asc())
        )
    )
    executions = list(
        await session.scalars(
            select(ToolExecution)
            .where(ToolExecution.conversation_id == conversation.id)
            .order_by(ToolExecution.created_at.asc())
        )
    )
    return ToolAwareConversationResponse(
        id=conversation.id,
        title=conversation.title,
        persona=conversation_persona_response(conversation),
        messages=[message_response(message) for message in messages],
        tool_executions=[execution_response(execution) for execution in executions],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )
