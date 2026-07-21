from typing import Any

from app import communication_service

_original_mark_thread_read = communication_service.mark_thread_read


async def _mark_thread_read_and_refresh(
    session: Any,
    thread: Any,
    **kwargs: Any,
) -> None:
    await _original_mark_thread_read(session, thread, **kwargs)
    await session.refresh(thread)


def install_communication_route_patch() -> None:
    communication_service.mark_thread_read = _mark_thread_read_and_refresh
