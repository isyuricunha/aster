from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ModelCacheEntry,
    ModelEndpoint,
    ModelFallbackEntry,
    ModelPreferences,
    ModelProfile,
)
from app.openai_compatible import ModelEndpointError
from app.provider_instruction_roles import InstructionRole
from app.security import SecretCipher

FALLBACK_ERROR_CODES = {
    "chat_not_supported",
    "connection_error",
    "empty_response",
    "invalid_response",
    "rate_limited",
    "timeout",
    "upstream_error",
}


@dataclass(frozen=True, slots=True)
class GenerationParameters:
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    token_parameter: str = "max_tokens"
    reasoning_effort: str | None = None


@dataclass(frozen=True, slots=True)
class ModelTarget:
    model_id: UUID
    provider_model_id: str
    endpoint_id: UUID
    endpoint_name: str
    base_url: str
    api_key: str | None
    instruction_role: InstructionRole
    parameters: GenerationParameters


def can_fallback(error: ModelEndpointError) -> bool:
    return error.code in FALLBACK_ERROR_CODES


def _decrypt_api_key(endpoint: ModelEndpoint, cipher: SecretCipher) -> str | None:
    if endpoint.encrypted_api_key is None:
        return None
    return cipher.decrypt(endpoint.encrypted_api_key)


def _target(
    model: ModelCacheEntry,
    endpoint: ModelEndpoint,
    profile: ModelProfile | None,
    cipher: SecretCipher,
) -> ModelTarget | None:
    supports_chat = profile.supports_chat if profile else True
    supports_streaming = profile.supports_streaming if profile else True
    unavailable = (
        not endpoint.enabled
        or not model.is_available
        or not supports_chat
        or not supports_streaming
    )
    if unavailable:
        return None
    return ModelTarget(
        model_id=model.id,
        provider_model_id=model.model_id,
        endpoint_id=endpoint.id,
        endpoint_name=endpoint.name,
        base_url=endpoint.base_url,
        api_key=_decrypt_api_key(endpoint, cipher),
        instruction_role=profile.instruction_role if profile else "system",
        parameters=GenerationParameters(
            temperature=profile.temperature if profile else None,
            top_p=profile.top_p if profile else None,
            max_output_tokens=profile.max_output_tokens if profile else None,
            token_parameter=profile.token_parameter if profile else "max_tokens",
            reasoning_effort=profile.reasoning_effort if profile else None,
        ),
    )


async def _model_row(
    session: AsyncSession,
    model_id: UUID,
) -> tuple[ModelCacheEntry, ModelEndpoint, ModelProfile | None] | None:
    return (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint, ModelProfile)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .outerjoin(ModelProfile, ModelProfile.model_id == ModelCacheEntry.id)
            .where(ModelCacheEntry.id == model_id)
        )
    ).one_or_none()


async def resolve_chat_targets(
    session: AsyncSession,
    cipher: SecretCipher,
) -> list[ModelTarget]:
    preferences = await session.get(ModelPreferences, 1)
    if preferences is None or preferences.primary_model_id is None:
        raise HTTPException(
            status_code=409,
            detail="Configure a primary model before starting a chat.",
        )
    fallback_ids = list(
        await session.scalars(
            select(ModelFallbackEntry.model_id).order_by(ModelFallbackEntry.position.asc())
        )
    )
    ordered_ids = list(dict.fromkeys([preferences.primary_model_id, *fallback_ids]))
    rows = (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint, ModelProfile)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .outerjoin(ModelProfile, ModelProfile.model_id == ModelCacheEntry.id)
            .where(ModelCacheEntry.id.in_(ordered_ids))
        )
    ).all()
    by_id = {model.id: (model, endpoint, profile) for model, endpoint, profile in rows}
    targets = [
        target
        for model_id in ordered_ids
        if (row := by_id.get(model_id)) is not None
        and (target := _target(*row, cipher)) is not None
    ]
    if targets:
        return targets
    raise HTTPException(
        status_code=409,
        detail="No configured chat model is currently available.",
    )


async def resolve_utility_target(
    session: AsyncSession,
    cipher: SecretCipher,
    *,
    purpose: str,
    max_output_tokens: int,
    temperature: float,
) -> ModelTarget:
    preferences = await session.get(ModelPreferences, 1)
    selected_id = None
    if preferences is not None:
        selected_id = preferences.utility_model_id or preferences.primary_model_id
    if selected_id is None:
        raise HTTPException(
            status_code=409,
            detail=f"Configure a Utility or Primary model before {purpose}.",
        )
    row = await _model_row(session, selected_id)
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="The selected Utility model no longer exists.",
        )
    target = _target(*row, cipher)
    if target is None:
        raise HTTPException(
            status_code=409,
            detail="The selected Utility model is unavailable.",
        )
    configured_limit = target.parameters.max_output_tokens
    bounded_limit = (
        min(configured_limit, max_output_tokens)
        if configured_limit is not None
        else max_output_tokens
    )
    return ModelTarget(
        model_id=target.model_id,
        provider_model_id=target.provider_model_id,
        endpoint_id=target.endpoint_id,
        endpoint_name=target.endpoint_name,
        base_url=target.base_url,
        api_key=target.api_key,
        instruction_role=target.instruction_role,
        parameters=GenerationParameters(
            temperature=temperature,
            top_p=target.parameters.top_p,
            max_output_tokens=bounded_limit,
            token_parameter=target.parameters.token_parameter,
            reasoning_effort=target.parameters.reasoning_effort,
        ),
    )


async def resolve_automation_targets(
    session: AsyncSession,
    cipher: SecretCipher,
    requested_model_id: UUID | None,
) -> list[ModelTarget]:
    if requested_model_id is None:
        return await resolve_chat_targets(session, cipher)
    row = await _model_row(session, requested_model_id)
    if row is None:
        raise HTTPException(status_code=409, detail="The automation model no longer exists.")
    target = _target(*row, cipher)
    if target is None:
        raise HTTPException(status_code=409, detail="The automation model is unavailable.")
    return [target]
