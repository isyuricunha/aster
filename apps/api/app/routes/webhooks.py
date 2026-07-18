import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation_models import Automation
from app.automation_schemas import WebhookAcceptedResponse
from app.automation_service import accept_webhook, hash_webhook_token
from app.config import settings
from app.db import get_session

router = APIRouter(prefix="/api", tags=["webhooks"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
WebhookToken = Annotated[
    str,
    Header(alias="X-Aster-Webhook-Token", min_length=20, max_length=512),
]


@router.post(
    "/webhooks/{automation_id}",
    response_model=WebhookAcceptedResponse,
)
async def receive_automation_webhook(
    automation_id: UUID,
    request: Request,
    session: SessionDep,
    webhook_token: WebhookToken,
) -> WebhookAcceptedResponse:
    body = await request.body()
    if len(body) > settings.aster_webhook_max_bytes:
        raise HTTPException(status_code=413, detail="Webhook payload is too large.")

    automation = await session.get(Automation, automation_id)
    supplied_hash = hash_webhook_token(webhook_token)
    stored_hash = automation.webhook_token_hash if automation is not None else None
    valid = (
        automation is not None
        and automation.enabled
        and automation.trigger_type == "webhook"
        and stored_hash is not None
        and secrets.compare_digest(stored_hash, supplied_hash)
    )
    if not valid:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found.")

    webhook_status, run = await accept_webhook(
        session,
        token=webhook_token,
        body=body,
        headers={key.lower(): value for key, value in request.headers.items()},
    )
    return WebhookAcceptedResponse(
        status=webhook_status,
        run_id=run.id if run else None,
    )
