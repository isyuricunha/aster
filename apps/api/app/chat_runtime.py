import asyncio
from uuid import UUID


class GenerationRegistry:
    def __init__(self) -> None:
        self._events: dict[UUID, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    async def register(self, message_id: UUID) -> asyncio.Event:
        async with self._lock:
            event = asyncio.Event()
            self._events[message_id] = event
            return event

    async def stop(self, message_id: UUID) -> bool:
        async with self._lock:
            event = self._events.get(message_id)
            if event is None:
                return False
            event.set()
            return True

    async def unregister(self, message_id: UUID) -> None:
        async with self._lock:
            self._events.pop(message_id, None)


generation_registry = GenerationRegistry()
