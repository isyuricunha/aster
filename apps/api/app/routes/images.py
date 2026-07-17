from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.dependencies import get_image_client, get_media_store, get_secret_cipher
from app.image_models import ImageModelProfile, ImageOperation
from app.image_provider import OpenAICompatibleImageClient
from app.image_schemas import (
    ImageGalleryResponse,
    ImageModelProfileResponse,
    ImageModelProfileUpdate,
    ImageOperationCreate,
    ImageOperationResponse,
    MediaAssetResponse,
)
from app.image_service import (
    asset_response,
    create_upload_asset,
    delete_asset_if_unreferenced,
    execute_image_operation,
    get_asset,
    image_profile_response,
    operation_response,
)
from app.image_storage import ImageValidationError, PrivateMediaStore
from app.models import ModelCacheEntry, ModelEndpoint
from app.openai_compatible import ModelEndpointError
from app.security import SecretCipher

router = APIRouter(prefix="/api", tags=["images"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ImageClientDep = Annotated[OpenAICompatibleImageClient, Depends(get_image_client)]
StoreDep = Annotated[PrivateMediaStore, Depends(get_media_store)]
CipherDep = Annotated[SecretCipher, Depends(get_secret_cipher)]


async def _get_operation(session: AsyncSession, operation_id: UUID) -> ImageOperation:
    operation = await session.get(ImageOperation, operation_id)
    if operation is None:
        raise HTTPException(status_code=404, detail="Image operation not found")
    return operation


@router.get("/image-model-profiles", response_model=list[ImageModelProfileResponse])
async def list_image_model_profiles(session: SessionDep) -> list[ImageModelProfileResponse]:
    rows = (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint, ImageModelProfile)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .outerjoin(ImageModelProfile, ImageModelProfile.model_id == ModelCacheEntry.id)
            .order_by(ModelEndpoint.name, ModelCacheEntry.model_id)
        )
    ).all()
    return [
        await image_profile_response(session, model, endpoint, profile)
        for model, endpoint, profile in rows
    ]


@router.put(
    "/image-model-profiles/{model_id}",
    response_model=ImageModelProfileResponse,
)
async def update_image_model_profile(
    model_id: UUID,
    payload: ImageModelProfileUpdate,
    session: SessionDep,
) -> ImageModelProfileResponse:
    row = (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .where(ModelCacheEntry.id == model_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found")
    model, endpoint = row
    profile = await session.get(ImageModelProfile, model.id)
    if profile is None:
        profile = ImageModelProfile(model_id=model.id)
        session.add(profile)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return await image_profile_response(session, model, endpoint, profile)


@router.post(
    "/media-assets/uploads",
    response_model=MediaAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image_asset(
    request: Request,
    session: SessionDep,
    store: StoreDep,
    filename: Annotated[str, Query(min_length=1, max_length=255)],
) -> MediaAssetResponse:
    data = await request.body()
    try:
        asset = await create_upload_asset(
            session,
            store=store,
            data=data,
            filename=filename,
            settings=settings,
        )
    except ImageValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return asset_response(asset)


@router.get("/media-assets/{asset_id}/content")
async def read_image_asset(
    asset_id: UUID,
    session: SessionDep,
    store: StoreDep,
) -> Response:
    try:
        asset = await get_asset(session, asset_id)
        data = store.read(asset.storage_key)
    except ImageValidationError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(
        content=data,
        media_type=asset.media_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/media-assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_asset(
    asset_id: UUID,
    session: SessionDep,
    store: StoreDep,
) -> Response:
    try:
        asset = await get_asset(session, asset_id)
        await delete_asset_if_unreferenced(session, asset=asset, store=store)
    except ImageValidationError as error:
        detail = str(error)
        raise HTTPException(
            status_code=409 if "referenced" in detail else 404,
            detail=detail,
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conversation_id}/image-operations",
    response_model=ImageOperationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_image_operation(
    conversation_id: UUID,
    payload: ImageOperationCreate,
    session: SessionDep,
    client: ImageClientDep,
    store: StoreDep,
    cipher: CipherDep,
) -> ImageOperationResponse:
    try:
        operation = await execute_image_operation(
            session,
            conversation_id=conversation_id,
            payload=payload,
            client=client,
            store=store,
            cipher=cipher,
            settings=settings,
        )
    except ImageValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ModelEndpointError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error
    await session.refresh(operation)
    return await operation_response(session, operation)


@router.get("/image-operations/{operation_id}", response_model=ImageOperationResponse)
async def read_image_operation(
    operation_id: UUID,
    session: SessionDep,
) -> ImageOperationResponse:
    operation = await _get_operation(session, operation_id)
    return await operation_response(session, operation)


@router.get("/image-gallery", response_model=ImageGalleryResponse)
async def list_image_gallery(
    session: SessionDep,
    conversation_id: UUID | None = None,
    operation_type: Literal["generation", "edit"] | None = None,
    operation_status: Literal["running", "completed", "failed"] | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 40,
) -> ImageGalleryResponse:
    conditions = []
    if conversation_id is not None:
        conditions.append(ImageOperation.conversation_id == conversation_id)
    if operation_type is not None:
        conditions.append(ImageOperation.operation_type == operation_type)
    if operation_status is not None:
        conditions.append(ImageOperation.status == operation_status)
    count_query = select(func.count(ImageOperation.id))
    list_query = select(ImageOperation)
    if conditions:
        count_query = count_query.where(*conditions)
        list_query = list_query.where(*conditions)
    total = int(await session.scalar(count_query) or 0)
    operations = list(
        await session.scalars(
            list_query.order_by(ImageOperation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return ImageGalleryResponse(
        items=[await operation_response(session, operation) for operation in operations],
        total=total,
        offset=offset,
        limit=limit,
    )
