from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.message_composition import MessageRole, PersonaConfiguration, compose_messages
from app.models import PersonaSettings
from app.schemas import (
    CanonicalMessageResponse,
    CompositionPreviewRequest,
    CompositionPreviewResponse,
    PersonaResponse,
    PersonaUpdate,
)

router = APIRouter(prefix="/api", tags=["persona"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_or_create_persona(session: AsyncSession) -> PersonaSettings:
    persona = await session.get(PersonaSettings, 1)
    if persona is None:
        persona = PersonaSettings(id=1)
        session.add(persona)
        await session.flush()
    return persona


def _persona_response(persona: PersonaSettings) -> PersonaResponse:
    return PersonaResponse(
        name=persona.name,
        instructions=persona.instructions,
        enabled=persona.enabled,
        instruction_role=persona.instruction_role,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )


def _persona_configuration(persona: PersonaSettings) -> PersonaConfiguration:
    return PersonaConfiguration(
        name=persona.name,
        instructions=persona.instructions,
        enabled=persona.enabled,
        instruction_role=MessageRole(persona.instruction_role),
    )


@router.get("/persona", response_model=PersonaResponse)
async def get_persona(session: SessionDep) -> PersonaResponse:
    persona = await _get_or_create_persona(session)
    await session.commit()
    await session.refresh(persona)
    return _persona_response(persona)


@router.put("/persona", response_model=PersonaResponse)
async def update_persona(payload: PersonaUpdate, session: SessionDep) -> PersonaResponse:
    persona = await _get_or_create_persona(session)
    persona.name = payload.name
    persona.instructions = payload.instructions
    persona.enabled = payload.enabled
    persona.instruction_role = payload.instruction_role
    await session.commit()
    await session.refresh(persona)
    return _persona_response(persona)


@router.post("/message-composition/preview", response_model=CompositionPreviewResponse)
async def preview_message_composition(
    payload: CompositionPreviewRequest,
    session: SessionDep,
) -> CompositionPreviewResponse:
    persona = await _get_or_create_persona(session)
    await session.commit()
    messages = compose_messages(
        persona=_persona_configuration(persona),
        current_user_message=payload.user_message,
    )
    return CompositionPreviewResponse(
        messages=[
            CanonicalMessageResponse(
                role=message.role.value,
                source=message.source.value,
                content=message.content,
            )
            for message in messages
        ]
    )
