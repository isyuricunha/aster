import asyncio
import os
import socket
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

from app.automation_execution import execute_run
from app.automation_service import (
    claim_next_run,
    enqueue_due_automations,
    recover_expired_automation_runs,
    renew_run_lease,
)
from app.config import settings
from app.db import AsyncSessionFactory, engine
from app.dependencies import get_openai_client, get_secret_cipher


async def _heartbeat(run_id, worker_id: str) -> None:
    interval = max(5, settings.aster_automation_heartbeat_seconds)
    while True:
        await asyncio.sleep(interval)
        async with AsyncSessionFactory() as session:
            renewed = await renew_run_lease(
                session,
                run_id=run_id,
                worker_id=worker_id,
                lease_seconds=settings.aster_automation_lease_seconds,
            )
        if not renewed:
            return


async def run_worker() -> None:
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
    client = get_openai_client()
    cipher = get_secret_cipher()
    async with AsyncSessionFactory() as session:
        await recover_expired_automation_runs(session)
    Path("/tmp/aster-worker-ready").touch()
    try:
        while True:
            async with AsyncSessionFactory() as session:
                await enqueue_due_automations(
                    session, limit=settings.aster_automation_scheduler_batch_size
                )
            async with AsyncSessionFactory() as session:
                run = await claim_next_run(
                    session,
                    worker_id=worker_id,
                    lease_seconds=settings.aster_automation_lease_seconds,
                )
            if run is None:
                await asyncio.sleep(settings.aster_automation_poll_seconds)
                continue
            heartbeat = asyncio.create_task(_heartbeat(run.id, worker_id))
            try:
                await execute_run(
                    AsyncSessionFactory,
                    run_id=run.id,
                    worker_id=worker_id,
                    client=client,
                    cipher=cipher,
                    settings=settings,
                )
            finally:
                heartbeat.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat
    finally:
        Path("/tmp/aster-worker-ready").unlink(missing_ok=True)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_worker())
