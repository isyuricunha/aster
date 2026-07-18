from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.model_profile_schemas import (
    FallbackModelResponse,
    ModelProfileResponse,
    ModelProfileUpdate,
    ModelRoutingResponse,
    ModelRoutingUpdate,
)
from app.models import (
    ModelCacheEntry,
    ModelEndpoint,
    ModelFallbackEntry,
    ModelPreferences,
    ModelProfile,
)

router = APIRouter(prefix="/api", tags=["models"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _model_row(
    session: AsyncSession,
    model_id: UUID,
) -> tuple[ModelCacheEntry, ModelEndpoint, ModelProfile | None]:
    row = (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint, ModelProfile)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .outerjoin(ModelProfile, ModelProfile.model_id == ModelCacheEntry.id)
            .where(ModelCacheEntry.id == model_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return row


def _profile_response(
    model: ModelCacheEntry,
    endpoint: ModelEndpoint,
    profile: ModelProfile | None,
) -> ModelProfileResponse:
    return ModelProfileResponse(
        model_id=model.id,
        endpoint_id=endpoint.id,
        endpoint_name=endpoint.name,
        provider_model_id=model.model_id,
        display_name=profile.display_name if profile else None,
        context_window=profile.context_window if profile else None,
        max_output_tokens=profile.max_output_tokens if profile else None,
        token_parameter=profile.token_parameter if profile else "max_tokens",
        instruction_role=profile.instruction_role if profile else "system",
        temperature=profile.temperature if profile else None,
        top_p=profile.top_p if profile else None,
        reasoning_effort=profile.reasoning_effort if profile else None,
        supports_chat=profile.supports_chat if profile else True,
        supports_streaming=profile.supports_streaming if profile else True,
        endpoint_enabled=endpoint.enabled,
        is_available=model.is_available,
        created_at=profile.created_at if profile else None,
        updated_at=profile.updated_at if profile else None,
    )


def _fallback_response(
    model: ModelCacheEntry,
    endpoint: ModelEndpoint,
    profile: ModelProfile | None,
) -> FallbackModelResponse:
    return FallbackModelResponse(
        id=model.id,
        endpoint_id=endpoint.id,
        endpoint_name=endpoint.name,
        model_id=model.model_id,
        display_name=profile.display_name if profile else None,
        endpoint_enabled=endpoint.enabled,
        is_available=model.is_available,
        supports_chat=profile.supports_chat if profile else True,
        supports_streaming=profile.supports_streaming if profile else True,
    )


@router.get("/model-profiles/{model_id}", response_model=ModelProfileResponse)
async def get_model_profile(
    model_id: UUID,
    session: SessionDep,
) -> ModelProfileResponse:
    return _profile_response(*await _model_row(session, model_id))


@router.put("/model-profiles/{model_id}", response_model=ModelProfileResponse)
async def update_model_profile(
    model_id: UUID,
    payload: ModelProfileUpdate,
    session: SessionDep,
) -> ModelProfileResponse:
    model, endpoint, profile = await _model_row(session, model_id)
    if profile is None:
        profile = ModelProfile(model_id=model.id)
        session.add(profile)

    for field_name, value in payload.model_dump().items():
        setattr(profile, field_name, value)

    await session.commit()
    await session.refresh(profile)
    return _profile_response(model, endpoint, profile)


@router.delete("/model-profiles/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def reset_model_profile(
    model_id: UUID,
    session: SessionDep,
) -> Response:
    await _model_row(session, model_id)
    await session.execute(delete(ModelProfile).where(ModelProfile.model_id == model_id))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _routing_response(session: AsyncSession) -> ModelRoutingResponse:
    rows = (
        await session.execute(
            select(ModelFallbackEntry, ModelCacheEntry, ModelEndpoint, ModelProfile)
            .join(ModelCacheEntry, ModelCacheEntry.id == ModelFallbackEntry.model_id)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .outerjoin(ModelProfile, ModelProfile.model_id == ModelCacheEntry.id)
            .order_by(ModelFallbackEntry.position.asc())
        )
    ).all()
    return ModelRoutingResponse(
        fallbacks=[
            _fallback_response(model, endpoint, profile)
            for _, model, endpoint, profile in rows
        ]
    )


@router.get("/model-routing", response_model=ModelRoutingResponse)
async def get_model_routing(session: SessionDep) -> ModelRoutingResponse:
    return await _routing_response(session)


@router.put("/model-routing", response_model=ModelRoutingResponse)
async def update_model_routing(
    payload: ModelRoutingUpdate,
    session: SessionDep,
) -> ModelRoutingResponse:
    preferences = await session.get(ModelPreferences, 1)
    primary_id = preferences.primary_model_id if preferences else None
    if primary_id is not None and primary_id in payload.fallback_model_ids:
        raise HTTPException(status_code=422, detail="Primary model cannot also be a fallback")

    if payload.fallback_model_ids:
        rows = (
            await session.execute(
                select(ModelCacheEntry, ModelEndpoint, ModelProfile)
                .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
                .outerjoin(ModelProfile, ModelProfile.model_id == ModelCacheEntry.id)
                .where(ModelCacheEntry.id.in_(payload.fallback_model_ids))
            )
        ).all()
        by_id = {model.id: (model, endpoint, profile) for model, endpoint, profile in rows}
        if set(by_id) != set(payload.fallback_model_ids):
            raise HTTPException(status_code=422, detail="One or more fallback models do not exist")

        for model_id in payload.fallback_model_ids:
            model, endpoint, profile = by_id[model_id]
            supports_chat = profile.supports_chat if profile else True
            supports_streaming = profile.supports_streaming if profile else True
            if not endpoint.enabled:
                raise HTTPException(
                    status_code=422,
                    detail=f"Fallback model {model.model_id} uses a disabled endpoint",
                )
            if not supports_chat or not supports_streaming:
                raise HTTPException(
                    status_code=422,
                    detail=f"Fallback model {model.model_id} is not enabled for streaming chat",
                )

    await session.execute(delete(ModelFallbackEntry))
    session.add_all(
        [
            ModelFallbackEntry(model_id=model_id, position=position)
            for position, model_id in enumerate(payload.fallback_model_ids)
        ]
    )
    await session.commit()
    return await _routing_response(session)
