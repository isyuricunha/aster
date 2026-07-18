import fnmatch
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_dispatch_models import AgentMessageDispatch
from app.agent_models import Agent, AgentCommunicationRule, AgentRun
from app.agent_queue import agent_control, enqueue_agent_run
from app.communication_models import (
    CommunicationAccount,
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationThread,
)
from app.config import Settings


def _matches(rule: AgentCommunicationRule, message: CommunicationMessage) -> bool:
    sender = (message.sender_address or message.sender_name or "").casefold()
    if rule.sender_pattern and not fnmatch.fnmatchcase(
        sender,
        rule.sender_pattern.casefold(),
    ):
        return False
    if rule.source_ids:
        candidates = {
            value.casefold()
            for value in (message.source_id, message.sender_address)
            if value
        }
        allowed = {item.casefold() for item in rule.source_ids}
        if not candidates.intersection(allowed):
            return False
    if (
        rule.body_contains
        and rule.body_contains.casefold() not in message.content_text.casefold()
    ):
        return False
    if rule.require_mention and not bool(message.metadata.get("mentioned_bot")):
        return False
    return True


async def _payload(
    session: AsyncSession,
    *,
    account: CommunicationAccount,
    thread: CommunicationThread,
    message: CommunicationMessage,
    maximum: int,
) -> dict[str, object]:
    attachments = list(
        await session.scalars(
            select(CommunicationAttachment).where(
                CommunicationAttachment.message_id == message.id
            )
        )
    )
    return {
        "type": "communication.message.received",
        "account": {
            "id": str(account.id),
            "name": account.name,
            "kind": account.kind,
        },
        "thread": {
            "id": str(thread.id),
            "title": thread.title,
            "kind": thread.kind,
        },
        "message": {
            "id": str(message.id),
            "source_id": message.source_id,
            "sender_name": message.sender_name,
            "sender_address": message.sender_address,
            "subject": message.subject,
            "content": message.content_text[:maximum],
            "content_truncated": len(message.content_text) > maximum,
            "sent_at": message.sent_at.isoformat(),
            "attachments": [
                {
                    "id": str(attachment.id),
                    "filename": attachment.filename,
                    "media_type": attachment.media_type,
                    "size_bytes": attachment.size_bytes,
                }
                for attachment in attachments
            ],
        },
    }


async def dispatch_agent_communication_events(
    session: AsyncSession,
    *,
    settings: Settings,
    limit: int,
) -> int:
    control = await agent_control(session)
    if control.emergency_stop:
        await session.commit()
        return 0
    rows = (
        await session.execute(
            select(
                AgentCommunicationRule,
                Agent,
                CommunicationMessage,
                CommunicationThread,
                CommunicationAccount,
            )
            .join(Agent, Agent.id == AgentCommunicationRule.agent_id)
            .join(
                CommunicationMessage,
                CommunicationMessage.account_id == AgentCommunicationRule.account_id,
            )
            .join(
                CommunicationThread,
                CommunicationThread.id == CommunicationMessage.thread_id,
            )
            .join(
                CommunicationAccount,
                CommunicationAccount.id == CommunicationMessage.account_id,
            )
            .outerjoin(
                AgentMessageDispatch,
                and_(
                    AgentMessageDispatch.rule_id == AgentCommunicationRule.id,
                    AgentMessageDispatch.message_id == CommunicationMessage.id,
                ),
            )
            .where(
                AgentCommunicationRule.enabled.is_(True),
                Agent.enabled.is_(True),
                Agent.paused.is_(False),
                Agent.trigger_type == "communication",
                CommunicationMessage.direction == "inbound",
                AgentMessageDispatch.id.is_(None),
            )
            .order_by(CommunicationMessage.received_at, AgentCommunicationRule.created_at)
            .limit(limit)
        )
    ).all()
    created = 0
    for rule, agent, message, thread, account in rows:
        if not _matches(rule, message):
            dispatch = AgentMessageDispatch(rule_id=rule.id, message_id=message.id)
            try:
                async with session.begin_nested():
                    session.add(dispatch)
                    await session.flush()
            except IntegrityError:
                continue
            continue
        occurrence_key = f"communication:{message.id}:{agent.id}"
        run = await enqueue_agent_run(
            session,
            agent,
            trigger_source="communication",
            occurrence_key=occurrence_key,
            scheduled_for=message.received_at,
            trigger_payload=await _payload(
                session,
                account=account,
                thread=thread,
                message=message,
                maximum=settings.aster_communication_message_max_characters,
            ),
        )
        if run is None:
            run = await session.scalar(
                select(AgentRun).where(AgentRun.occurrence_key == occurrence_key)
            )
        dispatch = AgentMessageDispatch(
            rule_id=rule.id,
            message_id=message.id,
            run_id=run.id if run else None,
        )
        try:
            async with session.begin_nested():
                session.add(dispatch)
                await session.flush()
        except IntegrityError:
            continue
        if run is not None and run.trigger_source == "communication":
            created += 1
    await session.commit()
    return created
