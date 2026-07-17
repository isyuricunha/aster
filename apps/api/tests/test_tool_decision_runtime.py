import asyncio
from uuid import uuid4

from app.tool_decision_runtime import ToolDecisionRegistry


async def test_decisions_for_one_conversation_are_serialized() -> None:
    registry = ToolDecisionRegistry()
    conversation_id = uuid4()
    first = await registry.acquire(conversation_id)

    waiting = asyncio.create_task(registry.acquire(conversation_id))
    await asyncio.sleep(0)
    assert waiting.done() is False

    await first.release()
    second = await asyncio.wait_for(waiting, timeout=1)
    await second.release()


async def test_decisions_for_different_conversations_do_not_block_each_other() -> None:
    registry = ToolDecisionRegistry()
    first = await registry.acquire(uuid4())
    second = await asyncio.wait_for(registry.acquire(uuid4()), timeout=1)

    await second.release()
    await first.release()
