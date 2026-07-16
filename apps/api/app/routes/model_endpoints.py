from datetime import UTC, datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_openai_client, get_secret_cipher
from app.models import ModelCacheEntry, ModelEndpoint, ModelPreferences, ModelSyncRun
from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.schemas import (
    CachedModelResponse,
    ConnectionTestResponse,
    EndpointCreate,
    EndpointResponse,
    EndpointUpdate,
    ManualModelCreate,
    ModelPreferencesResponse,
    ModelPreferencesUpdate,
    ModelSyncResponse,
    SelectedModelResponse,
)
from app.security import SecretCipher

router = APIRouter(prefix="/api", tags=["models"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]
ClientDep = Annotated[OpenAICompatibleClient, Depends(get_openai_client)]


async def _get_endpoint(session: AsyncSession, endpoint_id: UUID) -> ModelEndpoint:
    endpoint = await session.get(ModelEndpoint, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Model endpoint not found")
    return endpoint


async def _endpoint_response(
    session: AsyncSession, endpoint: ModelEndpoint
) -> EndpointResponse:
    cached_model_count = await session.scalar(
        select(func.count(ModelCacheEntry.id)).where(ModelCacheEntry.endpoint_id == endpoint.id)
    )
    latest_sync = await session.scalar(
        select(ModelSyncRun)
        .where(ModelSyncRun.endpoint_id == endpoint.id)
        .order_by(ModelSyncRun.started_at.desc())
        .limit(1)
    )
    latest_success = await session.scalar(
        select(ModelSyncRun)
        .where(
            ModelSyncRun.endpoint_id == endpoint.id,
            ModelSyncRun.status == "succeeded",
        )
        .order_by(ModelSyncRun.finished_at.desc())
        .limit(1)
    )
    return EndpointResponse(
        id=endpoint.id,
        name=endpoint.name,
        base_url=endpoint.base_url,
        enabled=endpoint.enabled,
        has_api_key=endpoint.encrypted_api_key is not None,
        cached_model_count=cached_model_count or 0,
        last_sync_status=latest_sync.status if latest_sync else None,
        last_sync_at=(latest_sync.finished_at or latest_sync.started_at) if latest_sync else None,
        last_successful_sync_at=latest_success.finished_at if latest_success else None,
        last_sync_error=latest_sync.error_message if latest_sync else None,
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
    )


def _decrypt_api_key(endpoint: ModelEndpoint, cipher: SecretCipher) -> str | None:
    if endpoint.encrypted_api_key is None:
        return None
    return cipher.decrypt(endpoint.encrypted_api_key)


def _raise_endpoint_error(error: ModelEndpointError) -> NoReturn:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.get("/model-endpoints", response_model=list[EndpointResponse])
async def list_endpoints(session: SessionDep) -> list[EndpointResponse]:
    endpoints = list(
        await session.scalars(select(ModelEndpoint).order_by(ModelEndpoint.name.asc()))
    )
    return [await _endpoint_response(session, endpoint) for endpoint in endpoints]


@router.post(
    "/model-endpoints",
    response_model=EndpointResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_endpoint(
    payload: EndpointCreate,
    session: SessionDep,
    cipher: CipherDep,
) -> EndpointResponse:
    endpoint = ModelEndpoint(
        name=payload.name,
        base_url=payload.base_url,
        encrypted_api_key=cipher.encrypt(payload.api_key) if payload.api_key else None,
        enabled=payload.enabled,
    )
    session.add(endpoint)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Endpoint name already exists") from error
    await session.refresh(endpoint)
    return await _endpoint_response(session, endpoint)


@router.patch("/model-endpoints/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: UUID,
    payload: EndpointUpdate,
    session: SessionDep,
    cipher: CipherDep,
) -> EndpointResponse:
    endpoint = await _get_endpoint(session, endpoint_id)
    fields = payload.model_dump(exclude_unset=True, exclude={"api_key", "clear_api_key"})
    for field_name, value in fields.items():
        if value is not None:
            setattr(endpoint, field_name, value)

    if payload.clear_api_key:
        endpoint.encrypted_api_key = None
    elif payload.api_key:
        endpoint.encrypted_api_key = cipher.encrypt(payload.api_key)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Endpoint name already exists") from error
    await session.refresh(endpoint)
    return await _endpoint_response(session, endpoint)


@router.delete("/model-endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: UUID,
    session: SessionDep,
) -> Response:
    endpoint = await _get_endpoint(session, endpoint_id)
    model_ids = list(
        await session.scalars(
            select(ModelCacheEntry.id).where(ModelCacheEntry.endpoint_id == endpoint.id)
        )
    )
    preferences = await session.get(ModelPreferences, 1)
    if preferences and model_ids:
        selected_ids = set(model_ids)
        if preferences.primary_model_id in selected_ids:
            preferences.primary_model_id = None
        if preferences.utility_model_id in selected_ids:
            preferences.utility_model_id = None
        if preferences.image_model_id in selected_ids:
            preferences.image_model_id = None

    await session.delete(endpoint)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/model-endpoints/{endpoint_id}/test", response_model=ConnectionTestResponse)
async def test_endpoint(
    endpoint_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
    client: ClientDep,
) -> ConnectionTestResponse:
    endpoint = await _get_endpoint(session, endpoint_id)
    try:
        models = await client.list_models(endpoint.base_url, _decrypt_api_key(endpoint, cipher))
    except ModelEndpointError as error:
        _raise_endpoint_error(error)
    return ConnectionTestResponse(
        models_found=len(models),
        message=f"Connection successful. {len(models)} models found.",
    )


@router.post("/model-endpoints/{endpoint_id}/sync", response_model=ModelSyncResponse)
async def sync_endpoint_models(
    endpoint_id: UUID,
    session: SessionDep,
    cipher: CipherDep,
    client: ClientDep,
) -> ModelSyncResponse:
    endpoint = await _get_endpoint(session, endpoint_id)
    sync_run = ModelSyncRun(endpoint_id=endpoint.id, status="running")
    session.add(sync_run)
    await session.flush()

    try:
        model_ids = await client.list_models(
            endpoint.base_url, _decrypt_api_key(endpoint, cipher)
        )
    except ModelEndpointError as error:
        sync_run.status = "failed"
        sync_run.error_code = error.code
        sync_run.error_message = error.message[:500]
        sync_run.finished_at = datetime.now(UTC)
        await session.commit()
        _raise_endpoint_error(error)

    synchronized_at = datetime.now(UTC)
    cached_entries = {
        entry.model_id: entry
        for entry in await session.scalars(
            select(ModelCacheEntry).where(ModelCacheEntry.endpoint_id == endpoint.id)
        )
    }

    for entry in cached_entries.values():
        if not entry.is_manual:
            entry.is_available = False

    for model_id in model_ids:
        entry = cached_entries.get(model_id)
        if entry is None:
            session.add(
                ModelCacheEntry(
                    endpoint_id=endpoint.id,
                    model_id=model_id,
                    is_available=True,
                    first_seen_at=synchronized_at,
                    last_seen_at=synchronized_at,
                )
            )
        else:
            entry.is_available = True
            entry.last_seen_at = synchronized_at
            if entry.first_seen_at is None:
                entry.first_seen_at = synchronized_at

    sync_run.status = "succeeded"
    sync_run.models_found = len(model_ids)
    sync_run.finished_at = synchronized_at
    await session.commit()
    return ModelSyncResponse(models_found=len(model_ids), synchronized_at=synchronized_at)


@router.get("/models", response_model=list[CachedModelResponse])
async def list_cached_models(
    session: SessionDep,
    endpoint_id: UUID | None = None,
) -> list[CachedModelResponse]:
    query = (
        select(ModelCacheEntry, ModelEndpoint.name)
        .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
        .order_by(ModelEndpoint.name.asc(), ModelCacheEntry.model_id.asc())
    )
    if endpoint_id is not None:
        query = query.where(ModelCacheEntry.endpoint_id == endpoint_id)

    rows = (await session.execute(query)).all()
    return [
        CachedModelResponse(
            id=entry.id,
            endpoint_id=entry.endpoint_id,
            endpoint_name=endpoint_name,
            model_id=entry.model_id,
            is_manual=entry.is_manual,
            is_available=entry.is_available,
            first_seen_at=entry.first_seen_at,
            last_seen_at=entry.last_seen_at,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        for entry, endpoint_name in rows
    ]


@router.post(
    "/model-endpoints/{endpoint_id}/models",
    response_model=CachedModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_manual_model(
    endpoint_id: UUID,
    payload: ManualModelCreate,
    session: SessionDep,
) -> CachedModelResponse:
    endpoint = await _get_endpoint(session, endpoint_id)
    entry = await session.scalar(
        select(ModelCacheEntry).where(
            ModelCacheEntry.endpoint_id == endpoint.id,
            ModelCacheEntry.model_id == payload.model_id,
        )
    )
    if entry is None:
        entry = ModelCacheEntry(
            endpoint_id=endpoint.id,
            model_id=payload.model_id,
            is_manual=True,
            is_available=True,
        )
        session.add(entry)
    else:
        entry.is_manual = True
        entry.is_available = True

    await session.commit()
    await session.refresh(entry)
    return CachedModelResponse(
        id=entry.id,
        endpoint_id=entry.endpoint_id,
        endpoint_name=endpoint.name,
        model_id=entry.model_id,
        is_manual=entry.is_manual,
        is_available=entry.is_available,
        first_seen_at=entry.first_seen_at,
        last_seen_at=entry.last_seen_at,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


async def _selected_model(
    session: AsyncSession, model_id: UUID | None
) -> SelectedModelResponse | None:
    if model_id is None:
        return None
    row = (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .where(ModelCacheEntry.id == model_id)
        )
    ).one_or_none()
    if row is None:
        return None
    entry, endpoint = row
    return SelectedModelResponse(
        id=entry.id,
        endpoint_id=endpoint.id,
        endpoint_name=endpoint.name,
        model_id=entry.model_id,
        endpoint_enabled=endpoint.enabled,
        is_available=entry.is_available,
    )


async def _preferences_response(
    session: AsyncSession, preferences: ModelPreferences
) -> ModelPreferencesResponse:
    primary = await _selected_model(session, preferences.primary_model_id)
    utility = await _selected_model(session, preferences.utility_model_id)
    image = await _selected_model(session, preferences.image_model_id)
    return ModelPreferencesResponse(
        primary=primary,
        utility=utility,
        image=image,
        resolved_utility=utility or primary,
    )


async def _get_or_create_preferences(session: AsyncSession) -> ModelPreferences:
    preferences = await session.get(ModelPreferences, 1)
    if preferences is None:
        preferences = ModelPreferences(id=1)
        session.add(preferences)
        await session.flush()
    return preferences


@router.get("/model-preferences", response_model=ModelPreferencesResponse)
async def get_model_preferences(
    session: SessionDep,
) -> ModelPreferencesResponse:
    preferences = await _get_or_create_preferences(session)
    await session.commit()
    return await _preferences_response(session, preferences)


@router.put("/model-preferences", response_model=ModelPreferencesResponse)
async def update_model_preferences(
    payload: ModelPreferencesUpdate,
    session: SessionDep,
) -> ModelPreferencesResponse:
    requested_ids = {
        model_id
        for model_id in (
            payload.primary_model_id,
            payload.utility_model_id,
            payload.image_model_id,
        )
        if model_id is not None
    }
    if requested_ids:
        rows = (
            await session.execute(
                select(ModelCacheEntry.id, ModelEndpoint.enabled)
                .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
                .where(ModelCacheEntry.id.in_(requested_ids))
            )
        ).all()
        found_ids = {model_id for model_id, _ in rows}
        if found_ids != requested_ids:
            raise HTTPException(status_code=422, detail="One or more selected models do not exist")
        if any(not enabled for _, enabled in rows):
            raise HTTPException(
                status_code=422,
                detail="Models from disabled endpoints cannot be selected",
            )

    preferences = await _get_or_create_preferences(session)
    preferences.primary_model_id = payload.primary_model_id
    preferences.utility_model_id = payload.utility_model_id
    preferences.image_model_id = payload.image_model_id
    await session.commit()
    await session.refresh(preferences)
    return await _preferences_response(session, preferences)
