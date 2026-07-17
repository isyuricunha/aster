from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.message_composition import MessageRole, PersonaConfiguration, compose_messages
from app.models import Persona, PersonaPreferences
from app.schemas import (
    CanonicalMessageResponse,
    CompositionPreviewRequest,
    CompositionPreviewResponse,
    LegacyPersonaResponse,
    LegacyPersonaUpdate,
    PersonaCreate,
    PersonaPreferencesResponse,
    PersonaPreferencesUpdate,
    PersonaResponse,
    PersonaTransferRequest,
    PersonaUpdate,
)

router = APIRouter(prefix="/api", tags=["persona"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_preferences(session: AsyncSession) -> PersonaPreferences:
    preferences = await session.get(PersonaPreferences, 1)
    if preferences is None:
        preferences = PersonaPreferences(id=1)
        session.add(preferences)
        await session.flush()
    return preferences


async def _get_persona(session: AsyncSession, persona_id: UUID) -> Persona:
    persona = await session.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


async def _get_default_persona(session: AsyncSession) -> Persona | None:
    preferences = await _get_preferences(session)
    if preferences.default_persona_id is None:
        return None
    return await session.get(Persona, preferences.default_persona_id)


def _persona_response(persona: Persona, default_persona_id: UUID | None) -> PersonaResponse:
    return PersonaResponse(
        id=persona.id,
        name=persona.name,
        description=persona.description,
        instructions=persona.instructions,
        enabled=persona.enabled,
        instruction_role=persona.instruction_role,
        is_default=persona.id == default_persona_id,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )


def _legacy_response(persona: Persona | None) -> LegacyPersonaResponse:
    if persona is None:
        now = datetime.now(UTC)
        return LegacyPersonaResponse(
            name="",
            instructions="",
            enabled=False,
            instruction_role="developer",
            created_at=now,
            updated_at=now,
        )
    return LegacyPersonaResponse(
        name=persona.name,
        instructions=persona.instructions,
        enabled=persona.enabled,
        instruction_role=persona.instruction_role,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )


def _persona_configuration(persona: Persona | None) -> PersonaConfiguration:
    if persona is None:
        return PersonaConfiguration(
            name="",
            instructions="",
            enabled=False,
            instruction_role=MessageRole.DEVELOPER,
        )
    return PersonaConfiguration(
        name=persona.name,
        instructions=persona.instructions,
        enabled=persona.enabled,
        instruction_role=MessageRole(persona.instruction_role),
    )


async def _create_persona(
    session: AsyncSession,
    payload: PersonaCreate | PersonaTransferRequest,
) -> Persona:
    persona = Persona(
        name=payload.name,
        description=payload.description,
        instructions=payload.instructions,
        enabled=payload.enabled,
        instruction_role=payload.instruction_role,
    )
    session.add(persona)
    await session.flush()

    preferences = await _get_preferences(session)
    if preferences.default_persona_id is None and persona.enabled:
        preferences.default_persona_id = persona.id
    await session.commit()
    await session.refresh(persona)
    return persona


@router.get("/personas", response_model=list[PersonaResponse])
async def list_personas(session: SessionDep) -> list[PersonaResponse]:
    preferences = await _get_preferences(session)
    statement = select(Persona).order_by(
        Persona.updated_at.desc(),
        Persona.name.asc(),
    )
    personas = list(await session.scalars(statement))
    await session.commit()
    return [
        _persona_response(persona, preferences.default_persona_id) for persona in personas
    ]


@router.post(
    "/personas",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_persona(payload: PersonaCreate, session: SessionDep) -> PersonaResponse:
    persona = await _create_persona(session, payload)
    preferences = await _get_preferences(session)
    return _persona_response(persona, preferences.default_persona_id)


@router.post(
    "/personas/import",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_persona(
    payload: PersonaTransferRequest,
    session: SessionDep,
) -> PersonaResponse:
    persona = await _create_persona(session, payload)
    preferences = await _get_preferences(session)
    return _persona_response(persona, preferences.default_persona_id)


@router.get("/persona-preferences", response_model=PersonaPreferencesResponse)
async def get_persona_preferences(session: SessionDep) -> PersonaPreferencesResponse:
    preferences = await _get_preferences(session)
    persona = (
        await session.get(Persona, preferences.default_persona_id)
        if preferences.default_persona_id is not None
        else None
    )
    await session.commit()
    return PersonaPreferencesResponse(
        default_persona=(
            _persona_response(persona, preferences.default_persona_id) if persona else None
        )
    )


@router.put("/persona-preferences", response_model=PersonaPreferencesResponse)
async def update_persona_preferences(
    payload: PersonaPreferencesUpdate,
    session: SessionDep,
) -> PersonaPreferencesResponse:
    preferences = await _get_preferences(session)
    persona = None
    if payload.default_persona_id is not None:
        persona = await _get_persona(session, payload.default_persona_id)
        if not persona.enabled:
            raise HTTPException(
                status_code=422,
                detail="A disabled persona cannot be the default persona.",
            )
    preferences.default_persona_id = payload.default_persona_id
    await session.commit()
    if persona is not None:
        await session.refresh(persona)
    return PersonaPreferencesResponse(
        default_persona=(
            _persona_response(persona, preferences.default_persona_id) if persona else None
        )
    )


@router.get("/personas/{persona_id}", response_model=PersonaResponse)
async def read_persona(persona_id: UUID, session: SessionDep) -> PersonaResponse:
    persona = await _get_persona(session, persona_id)
    preferences = await _get_preferences(session)
    await session.commit()
    return _persona_response(persona, preferences.default_persona_id)


@router.put("/personas/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: UUID,
    payload: PersonaUpdate,
    session: SessionDep,
) -> PersonaResponse:
    persona = await _get_persona(session, persona_id)
    persona.name = payload.name
    persona.description = payload.description
    persona.instructions = payload.instructions
    persona.enabled = payload.enabled
    persona.instruction_role = payload.instruction_role
    await session.commit()
    await session.refresh(persona)
    preferences = await _get_preferences(session)
    return _persona_response(persona, preferences.default_persona_id)


@router.post(
    "/personas/{persona_id}/duplicate",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_persona(persona_id: UUID, session: SessionDep) -> PersonaResponse:
    source = await _get_persona(session, persona_id)
    duplicate = Persona(
        name=f"{source.name} copy"[:120],
        description=source.description,
        instructions=source.instructions,
        enabled=source.enabled,
        instruction_role=source.instruction_role,
    )
    session.add(duplicate)
    await session.commit()
    await session.refresh(duplicate)
    preferences = await _get_preferences(session)
    return _persona_response(duplicate, preferences.default_persona_id)


@router.delete("/personas/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(persona_id: UUID, session: SessionDep) -> Response:
    persona = await _get_persona(session, persona_id)
    preferences = await _get_preferences(session)
    if preferences.default_persona_id == persona.id:
        preferences.default_persona_id = None
    await session.delete(persona)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/persona", response_model=LegacyPersonaResponse)
async def get_legacy_persona(session: SessionDep) -> LegacyPersonaResponse:
    persona = await _get_default_persona(session)
    await session.commit()
    return _legacy_response(persona)


@router.put("/persona", response_model=LegacyPersonaResponse)
async def update_legacy_persona(
    payload: LegacyPersonaUpdate,
    session: SessionDep,
) -> LegacyPersonaResponse:
    preferences = await _get_preferences(session)
    persona = await _get_default_persona(session)
    if persona is None:
        persona = Persona(
            name=payload.name,
            description="",
            instructions=payload.instructions,
            enabled=payload.enabled,
            instruction_role=payload.instruction_role,
        )
        session.add(persona)
        await session.flush()
        preferences.default_persona_id = persona.id
    else:
        persona.name = payload.name
        persona.instructions = payload.instructions
        persona.enabled = payload.enabled
        persona.instruction_role = payload.instruction_role
    await session.commit()
    await session.refresh(persona)
    return _legacy_response(persona)


@router.post("/message-composition/preview", response_model=CompositionPreviewResponse)
async def preview_message_composition(
    payload: CompositionPreviewRequest,
    session: SessionDep,
) -> CompositionPreviewResponse:
    if payload.use_default_persona:
        persona = await _get_default_persona(session)
    elif payload.persona_id is not None:
        persona = await _get_persona(session, payload.persona_id)
    else:
        persona = None
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
