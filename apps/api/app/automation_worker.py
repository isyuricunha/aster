import asyncio
import logging
import os
import socket
from contextlib import suppress
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.automation_execution import execute_run
from app.automation_queue import (
    claim_next_run,
    enqueue_due_automations,
    recover_expired_automation_runs,
    renew_run_lease,
)
from app.config import settings
from app.db import AsyncSessionFactory, engine
from app.dependencies import get_openai_client, get_secret_cipher

logger = logging.getLogger(__name__)


class LeaseLostError(RuntimeError):
    pass


async def _heartbeat(run_id: UUID, worker_id: str) -> None:
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


async def _execute_claimed(run_id: UUID, worker_id: str) -> None:
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
    heartbeat = asyncio.create_task(_heartbeat(run_id, worker_id))
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


async def _set_ready(path: Path, ready: bool) -> None:
    if ready:
        await asyncio.to_thread(path.touch)
    else:
        await asyncio.to_thread(path.unlink, missing_ok=True)


async def run_worker() -> None:
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
    ready_path = Path("/tmp/aster-worker-ready")
    ready = False
    try:
        while True:
            try:
                async with AsyncSessionFactory() as session:
                    await recover_expired_automation_runs(session)
                    await enqueue_due_automations(
                        session,
                        limit=settings.aster_automation_scheduler_batch_size,
                    )
                if not ready:
                    await _set_ready(ready_path, True)
                    ready = True
                async with AsyncSessionFactory() as session:
                    run = await claim_next_run(
                        session,
                        worker_id=worker_id,
                        lease_seconds=settings.aster_automation_lease_seconds,
                    )
                if run is None:
                    await asyncio.sleep(settings.aster_automation_poll_seconds)
                    continue
                await _execute_claimed(run.id, worker_id)
            except (LeaseLostError, OSError, SQLAlchemyError) as error:
                logger.warning("Automation worker is waiting for recovery: %s", error)
                await asyncio.sleep(settings.aster_automation_poll_seconds)
            except Exception:
                logger.exception("Unexpected automation worker failure")
                await asyncio.sleep(settings.aster_automation_poll_seconds)
    finally:
        await _set_ready(ready_path, False)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_worker())
