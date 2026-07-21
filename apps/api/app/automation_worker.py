import asyncio
import logging
import os
import socket
from contextlib import suppress
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.agent_communication_dispatch import dispatch_agent_communication_events
from app.agent_execution import execute_agent_run
from app.agent_queue import (
    claim_next_agent_run,
    enqueue_due_agents,
    recover_expired_agent_runs,
    renew_agent_run_lease,
)
from app.automation_execution import execute_run
from app.automation_queue import (
    claim_next_run,
    enqueue_due_automations,
    recover_expired_automation_runs,
    renew_run_lease,
)
from app.builtin_tasks import ensure_builtin_tasks
from app.communication_worker import sync_due_communication_account
from app.config import settings
from app.db import AsyncSessionFactory, engine
from app.dependencies import (
    get_communication_store,
    get_mcp_client,
    get_openai_client,
    get_secret_cipher,
)

logger = logging.getLogger(__name__)


class LeaseLostError(RuntimeError):
    pass


async def _automation_heartbeat(run_id: UUID, worker_id: str) -> None:
    interval = max(5, settings.aster_automation_heartbeat_seconds)
    while True:
        await asyncio.sleep(interval)
        try:
            async with AsyncSessionFactory() as session:
                renewed = await renew_run_lease(
                    session,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=settings.aster_automation_lease_seconds,
                )
        except (OSError, SQLAlchemyError):
            continue
        if not renewed:
            raise LeaseLostError("The automation worker lost its run lease.")


async def _agent_heartbeat(run_id: UUID, worker_id: str) -> None:
    interval = max(5, settings.aster_agent_heartbeat_seconds)
    while True:
        await asyncio.sleep(interval)
        try:
            async with AsyncSessionFactory() as session:
                renewed = await renew_agent_run_lease(
                    session,
                    run_id=run_id,
                    worker_id=worker_id,
                    lease_seconds=settings.aster_agent_lease_seconds,
                )
        except (OSError, SQLAlchemyError):
            continue
        if not renewed:
            raise LeaseLostError("The automation worker lost its agent run lease.")


async def _wait_with_heartbeat(
    execution: asyncio.Task[None],
    heartbeat: asyncio.Task[None],
) -> None:
    done, _ = await asyncio.wait(
        {execution, heartbeat},
        return_when=asyncio.FIRST_COMPLETED,
    )
    if heartbeat in done:
        error = heartbeat.exception()
        if error is not None:
            execution.cancel()
            with suppress(asyncio.CancelledError):
                await execution
            raise error
    heartbeat.cancel()
    with suppress(asyncio.CancelledError):
        await heartbeat
    await execution


async def _execute_claimed_automation(run_id: UUID, worker_id: str) -> None:
    execution = asyncio.create_task(
        execute_run(
            AsyncSessionFactory,
            run_id=run_id,
            worker_id=worker_id,
            client=get_openai_client(),
            cipher=get_secret_cipher(),
            settings=settings,
        )
    )
    heartbeat = asyncio.create_task(_automation_heartbeat(run_id, worker_id))
    await _wait_with_heartbeat(execution, heartbeat)


async def _execute_claimed_agent(run_id: UUID, worker_id: str) -> None:
    execution = asyncio.create_task(
        execute_agent_run(
            AsyncSessionFactory,
            run_id=run_id,
            worker_id=worker_id,
            client=get_openai_client(),
            mcp_client=get_mcp_client(),
            cipher=get_secret_cipher(),
            settings=settings,
        )
    )
    heartbeat = asyncio.create_task(_agent_heartbeat(run_id, worker_id))
    await _wait_with_heartbeat(execution, heartbeat)


async def _set_ready(path: Path, ready: bool) -> None:
    if ready:
        await asyncio.to_thread(path.touch)
    else:
        await asyncio.to_thread(path.unlink, missing_ok=True)


async def _schedule_background_work() -> None:
    async with AsyncSessionFactory() as session:
        await ensure_builtin_tasks(session)
        await recover_expired_automation_runs(session)
        await recover_expired_agent_runs(session)
        await enqueue_due_automations(
            session,
            limit=settings.aster_automation_scheduler_batch_size,
        )
        await enqueue_due_agents(
            session,
            limit=settings.aster_agent_scheduler_batch_size,
        )


async def _dispatch_communication_events() -> None:
    async with AsyncSessionFactory() as session:
        await dispatch_agent_communication_events(
            session,
            settings=settings,
            limit=settings.aster_agent_dispatch_batch_size,
        )


async def run_worker() -> None:
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
    ready_path = Path("/tmp/aster-worker-ready")
    ready = False
    cipher = get_secret_cipher()
    communication_store = get_communication_store()
    try:
        while True:
            try:
                await _schedule_background_work()
                await sync_due_communication_account(
                    AsyncSessionFactory,
                    worker_id=worker_id,
                    cipher=cipher,
                    store=communication_store,
                    settings=settings,
                )
                await _dispatch_communication_events()
                if not ready:
                    await _set_ready(ready_path, True)
                    ready = True
                async with AsyncSessionFactory() as session:
                    automation_run = await claim_next_run(
                        session,
                        worker_id=worker_id,
                        lease_seconds=settings.aster_automation_lease_seconds,
                    )
                if automation_run is not None:
                    await _execute_claimed_automation(automation_run.id, worker_id)
                    continue
                async with AsyncSessionFactory() as session:
                    agent_run = await claim_next_agent_run(
                        session,
                        worker_id=worker_id,
                        lease_seconds=settings.aster_agent_lease_seconds,
                    )
                if agent_run is not None:
                    await _execute_claimed_agent(agent_run.id, worker_id)
                    continue
                await asyncio.sleep(settings.aster_automation_poll_seconds)
            except (LeaseLostError, OSError, SQLAlchemyError) as error:
                logger.warning("Background worker is waiting for recovery: %s", error)
                await asyncio.sleep(settings.aster_automation_poll_seconds)
            except Exception:
                logger.exception("Unexpected background worker failure")
                await asyncio.sleep(settings.aster_automation_poll_seconds)
    finally:
        await _set_ready(ready_path, False)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_worker())
