import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.chat_generation import recover_interrupted_streams
from app.db import AsyncSessionFactory, engine

router = APIRouter(tags=["system"])
_recovery_lock = asyncio.Lock()
_recovery_complete = False


class HealthResponse(BaseModel):
    status: Literal["ok"]


async def _recover_interrupted_streams_once() -> None:
    global _recovery_complete
    if _recovery_complete:
        return
    async with _recovery_lock:
        if _recovery_complete:
            return
        async with AsyncSessionFactory() as session:
            await recover_interrupted_streams(session)
        _recovery_complete = True


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def ready() -> HealthResponse:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await _recover_interrupted_streams_once()
    except (OSError, SQLAlchemyError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        ) from error

    return HealthResponse(status="ok")
