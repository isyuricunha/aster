import asyncio
from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class _DecisionEntry:
    lock: asyncio.Lock
    users: int = 0


class ToolDecisionLease:
    def __init__(
        self,
        registry: "ToolDecisionRegistry",
        conversation_id: UUID,
        entry: _DecisionEntry,
    ) -> None:
        self._registry = registry
        self._conversation_id = conversation_id
        self._entry = entry
        self._released = False

    async def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._entry.lock.release()
        await self._registry._release(self._conversation_id, self._entry)


class ToolDecisionRegistry:
    def __init__(self) -> None:
        self._guard = asyncio.Lock()
        self._entries: dict[UUID, _DecisionEntry] = {}

    async def acquire(self, conversation_id: UUID) -> ToolDecisionLease:
        async with self._guard:
            entry = self._entries.setdefault(
                conversation_id,
                _DecisionEntry(lock=asyncio.Lock()),
            )
            entry.users += 1
        try:
            await entry.lock.acquire()
        except BaseException:
            await self._release(conversation_id, entry)
            raise
        return ToolDecisionLease(self, conversation_id, entry)

    async def _release(self, conversation_id: UUID, entry: _DecisionEntry) -> None:
        async with self._guard:
            entry.users -= 1
            if entry.users == 0 and not entry.lock.locked():
                self._entries.pop(conversation_id, None)


tool_decision_registry = ToolDecisionRegistry()
