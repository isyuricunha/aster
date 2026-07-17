from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_generation import ensure_no_active_generation, get_conversation
from app.config import Settings
from app.image_models import (
    ImageModelProfile,
    ImageOperation,
    ImageOperationInput,
    ImageOperationOutput,
    MediaAsset,
    MessageAttachment,
)
from app.image_provider import OpenAICompatibleImageClient
from app.image_schemas import (
    ImageModelProfileResponse,
    ImageOperationCreate,
    ImageOperationResponse,
    MediaAssetResponse,
    MessageAttachmentResponse,
)
from app.image_storage import (
    ImageValidationError,
    PrivateMediaStore,
    validate_and_sanitize_image,
)
from app.models import (
    ChatMessage,
    Conversation,
    ModelCacheEntry,
    ModelEndpoint,
    ModelPreferences,
)
from app.openai_compatible import ModelEndpointError
from app.security import SecretCipher
from app.tool_guards import ensure_no_pending_tool_confirmation


@dataclass(frozen=True, slots=True)
class ImageTarget:
    model: ModelCacheEntry
    endpoint: ModelEndpoint
    profile: ImageModelProfile
    api_key: str | None


async def image_profile_response(
    session: AsyncSession,
    model: ModelCacheEntry,
    endpoint: ModelEndpoint,
    profile: ImageModelProfile | None,
) -> ImageModelProfileResponse:
    values = profile or ImageModelProfile(model_id=model.id)
    return ImageModelProfileResponse(
        model_id=model.id,
        endpoint_id=endpoint.id,
        endpoint_name=endpoint.name,
        provider_model_id=model.model_id,
        supports_generation=values.supports_generation,
        supports_editing=values.supports_editing,
        supports_multiple_inputs=values.supports_multiple_inputs,
        supports_masks=values.supports_masks,
        max_input_images=values.max_input_images,
        default_size=values.default_size,
        default_quality=values.default_quality,
        default_output_format=values.default_output_format,
        default_background=values.default_background,
        default_count=values.default_count,
        default_input_fidelity=values.default_input_fidelity,
        provider_parameters=values.provider_parameters,
        endpoint_enabled=endpoint.enabled,
        is_available=model.is_available,
        created_at=profile.created_at if profile else None,
        updated_at=profile.updated_at if profile else None,
    )


def asset_response(asset: MediaAsset) -> MediaAssetResponse:
    return MediaAssetResponse(
        id=asset.id,
        source_type=asset.source_type,
        original_filename=asset.original_filename,
        media_type=asset.media_type,
        size_bytes=asset.size_bytes,
        content_sha256=asset.content_sha256,
        width=asset.width,
        height=asset.height,
        content_url=f"/api/media-assets/{asset.id}/content",
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def attachment_response(
    asset: MediaAsset,
    attachment_type: str,
    position: int,
) -> MessageAttachmentResponse:
    return MessageAttachmentResponse(
        **asset_response(asset).model_dump(),
        attachment_type=attachment_type,
        position=position,
    )


async def attachments_for_messages(
    session: AsyncSession,
    message_ids: list[UUID],
) -> dict[UUID, list[MessageAttachmentResponse]]:
    if not message_ids:
        return {}
    rows = (
        await session.execute(
            select(MessageAttachment, MediaAsset)
            .join(MediaAsset, MediaAsset.id == MessageAttachment.asset_id)
            .where(MessageAttachment.message_id.in_(message_ids))
            .order_by(MessageAttachment.message_id, MessageAttachment.position)
        )
    ).all()
    grouped: dict[UUID, list[MessageAttachmentResponse]] = {}
    for attachment, asset in rows:
        grouped.setdefault(attachment.message_id, []).append(
            attachment_response(asset, attachment.attachment_type, attachment.position)
        )
    return grouped


async def operation_response(
    session: AsyncSession,
    operation: ImageOperation,
) -> ImageOperationResponse:
    input_rows = (
        await session.execute(
            select(ImageOperationInput, MediaAsset)
            .join(MediaAsset, MediaAsset.id == ImageOperationInput.asset_id)
            .where(ImageOperationInput.operation_id == operation.id)
            .order_by(ImageOperationInput.position)
        )
    ).all()
    output_rows = (
        await session.execute(
            select(ImageOperationOutput, MediaAsset)
            .join(MediaAsset, MediaAsset.id == ImageOperationOutput.asset_id)
            .where(ImageOperationOutput.operation_id == operation.id)
            .order_by(ImageOperationOutput.position)
        )
    ).all()
    return ImageOperationResponse(
        id=operation.id,
        conversation_id=operation.conversation_id,
        user_message_id=operation.user_message_id,
        assistant_message_id=operation.assistant_message_id,
        operation_type=operation.operation_type,
        status=operation.status,
        model_cache_entry_id=operation.model_cache_entry_id,
        provider_model_id=operation.provider_model_id,
        prompt=operation.prompt,
        revised_prompt=operation.revised_prompt,
        parameters=operation.parameters,
        error_code=operation.error_code,
        error_message=operation.error_message,
        inputs=[
            attachment_response(asset, "input", item.position) for item, asset in input_rows
        ],
        outputs=[
            attachment_response(asset, "output", item.position) for item, asset in output_rows
        ],
        started_at=operation.started_at,
        finished_at=operation.finished_at,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
    )


async def create_upload_asset(
    session: AsyncSession,
    *,
    store: PrivateMediaStore,
    data: bytes,
    filename: str,
    settings: Settings,
) -> MediaAsset:
    image = validate_and_sanitize_image(
        data,
        max_bytes=settings.aster_image_upload_max_bytes,
        max_pixels=settings.aster_image_max_pixels,
    )
    safe_filename = Path(filename).name.strip()[:255] or None
    storage_key = store.write(image)
    asset = MediaAsset(
        source_type="upload",
        storage_key=storage_key,
        original_filename=safe_filename,
        media_type=image.media_type,
        size_bytes=len(image.data),
        content_sha256=image.sha256,
        width=image.width,
        height=image.height,
    )
    session.add(asset)
    try:
        await session.commit()
    except Exception:
        store.delete(storage_key)
        raise
    await session.refresh(asset)
    return asset


async def get_asset(session: AsyncSession, asset_id: UUID) -> MediaAsset:
    asset = await session.get(MediaAsset, asset_id)
    if asset is None:
        raise ImageValidationError("Image asset not found.")
    return asset


async def resolve_image_target(
    session: AsyncSession,
    cipher: SecretCipher,
    *,
    requested_model_id: UUID | None,
    editing: bool,
) -> ImageTarget:
    target_id = requested_model_id
    if target_id is None:
        preferences = await session.get(ModelPreferences, 1)
        if preferences is None:
            raise ImageValidationError("Configure an image-capable model before generating images.")
        target_id = preferences.image_model_id or preferences.primary_model_id
    if target_id is None:
        raise ImageValidationError("Configure an image-capable model before generating images.")
    row = (
        await session.execute(
            select(ModelCacheEntry, ModelEndpoint, ImageModelProfile)
            .join(ModelEndpoint, ModelEndpoint.id == ModelCacheEntry.endpoint_id)
            .outerjoin(ImageModelProfile, ImageModelProfile.model_id == ModelCacheEntry.id)
            .where(ModelCacheEntry.id == target_id)
        )
    ).one_or_none()
    if row is None:
        raise ImageValidationError("The selected image model no longer exists.")
    model, endpoint, profile = row
    if not endpoint.enabled or not model.is_available:
        raise ImageValidationError("The selected image model is unavailable.")
    if profile is None:
        raise ImageValidationError("Declare image capabilities for the selected model first.")
    if editing and not profile.supports_editing:
        raise ImageValidationError("The selected model does not support image editing.")
    if not editing and not profile.supports_generation:
        raise ImageValidationError("The selected model does not support image generation.")
    api_key = (
        cipher.decrypt(endpoint.encrypted_api_key)
        if endpoint.encrypted_api_key is not None
        else None
    )
    return ImageTarget(model=model, endpoint=endpoint, profile=profile, api_key=api_key)


def _resolved_parameters(
    payload: ImageOperationCreate,
    profile: ImageModelProfile,
) -> dict[str, object]:
    parameters = dict(profile.provider_parameters)
    values: dict[str, object | None] = {
        "size": payload.size or profile.default_size,
        "quality": payload.quality or profile.default_quality,
        "output_format": payload.output_format or profile.default_output_format,
        "background": payload.background or profile.default_background,
        "n": payload.count or profile.default_count,
        "input_fidelity": payload.input_fidelity or profile.default_input_fidelity,
    }
    parameters.update(payload.provider_parameters)
    for key, value in values.items():
        if value is not None:
            parameters[key] = value
    return parameters


def _title_from_prompt(prompt: str) -> str:
    normalized = " ".join(prompt.split())
    return normalized if len(normalized) <= 60 else f"{normalized[:57].rstrip()}..."


def _asset_filename(asset: MediaAsset) -> str:
    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(
        asset.media_type, "bin"
    )
    return asset.original_filename or f"{asset.id}.{extension}"


async def execute_image_operation(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    payload: ImageOperationCreate,
    client: OpenAICompatibleImageClient,
    store: PrivateMediaStore,
    cipher: SecretCipher,
    settings: Settings,
) -> ImageOperation:
    conversation = await get_conversation(session, conversation_id, for_update=True)
    await ensure_no_active_generation(session, conversation.id)
    await ensure_no_pending_tool_confirmation(session, conversation.id)
    editing = bool(payload.input_asset_ids)
    target = await resolve_image_target(
        session,
        cipher,
        requested_model_id=payload.model_id,
        editing=editing,
    )
    if len(payload.input_asset_ids) > settings.aster_image_max_inputs:
        raise ImageValidationError(
            f"Image operations accept at most {settings.aster_image_max_inputs} inputs."
        )
    if len(payload.input_asset_ids) > target.profile.max_input_images:
        raise ImageValidationError(
            f"The selected model accepts at most {target.profile.max_input_images} inputs."
        )
    if len(payload.input_asset_ids) > 1 and not target.profile.supports_multiple_inputs:
        raise ImageValidationError("The selected model accepts only one input image.")
    if payload.mask_asset_id is not None and not target.profile.supports_masks:
        raise ImageValidationError("The selected model does not support masks.")

    input_assets = [await get_asset(session, asset_id) for asset_id in payload.input_asset_ids]
    mask_asset = (
        await get_asset(session, payload.mask_asset_id)
        if payload.mask_asset_id is not None
        else None
    )
    parameters = _resolved_parameters(payload, target.profile)
    count = parameters.get("n", 1)
    if not isinstance(count, int) or count < 1 or count > settings.aster_image_max_outputs:
        raise ImageValidationError(
            f"Image operations may return at most {settings.aster_image_max_outputs} outputs."
        )

    messages = list(
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.position)
        )
    )
    next_position = messages[-1].position + 1 if messages else 1
    if not messages and conversation.title == "New chat":
        conversation.title = _title_from_prompt(payload.prompt)
    user_message = ChatMessage(
        conversation_id=conversation.id,
        role="user",
        content=payload.prompt,
        status="completed",
        position=next_position,
    )
    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        role="assistant",
        content="",
        status="streaming",
        model_id=target.model.model_id,
        position=next_position + 1,
    )
    session.add_all([user_message, assistant_message])
    await session.flush()
    operation = ImageOperation(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        model_cache_entry_id=target.model.id,
        operation_type="edit" if editing else "generation",
        status="running",
        provider_model_id=target.model.model_id,
        prompt=payload.prompt,
        parameters=parameters,
    )
    session.add(operation)
    await session.flush()
    for position, asset in enumerate(input_assets):
        session.add_all(
            [
                ImageOperationInput(
                    operation_id=operation.id,
                    asset_id=asset.id,
                    input_type="source",
                    position=position,
                ),
                MessageAttachment(
                    message_id=user_message.id,
                    asset_id=asset.id,
                    attachment_type="input",
                    position=position,
                ),
            ]
        )
    if mask_asset is not None:
        mask_position = len(input_assets)
        session.add(
            ImageOperationInput(
                operation_id=operation.id,
                asset_id=mask_asset.id,
                input_type="mask",
                position=mask_position,
            )
        )
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(operation)

    created_storage_keys: list[str] = []
    try:
        if editing:
            provider_images = await client.edit(
                base_url=target.endpoint.base_url,
                api_key=target.api_key,
                model_id=target.model.model_id,
                prompt=payload.prompt,
                images=[
                    (_asset_filename(asset), store.read(asset.storage_key), asset.media_type)
                    for asset in input_assets
                ],
                mask=(
                    (
                        _asset_filename(mask_asset),
                        store.read(mask_asset.storage_key),
                        mask_asset.media_type,
                    )
                    if mask_asset is not None
                    else None
                ),
                parameters=parameters,
            )
        else:
            provider_images = await client.generate(
                base_url=target.endpoint.base_url,
                api_key=target.api_key,
                model_id=target.model.model_id,
                prompt=payload.prompt,
                parameters=parameters,
            )
        if len(provider_images) > settings.aster_image_max_outputs:
            raise ImageValidationError("The provider returned too many image outputs.")
        revised_prompts = [item.revised_prompt for item in provider_images if item.revised_prompt]
        operation.revised_prompt = revised_prompts[0] if revised_prompts else None
        for position, item in enumerate(provider_images):
            validated = validate_and_sanitize_image(
                item.data,
                max_bytes=settings.aster_image_output_max_bytes,
                max_pixels=settings.aster_image_max_pixels,
            )
            storage_key = store.write(validated)
            created_storage_keys.append(storage_key)
            asset = MediaAsset(
                source_type="edited" if editing else "generated",
                storage_key=storage_key,
                original_filename=None,
                media_type=validated.media_type,
                size_bytes=len(validated.data),
                content_sha256=validated.sha256,
                width=validated.width,
                height=validated.height,
            )
            session.add(asset)
            await session.flush()
            session.add_all(
                [
                    ImageOperationOutput(
                        operation_id=operation.id,
                        asset_id=asset.id,
                        position=position,
                    ),
                    MessageAttachment(
                        message_id=assistant_message.id,
                        asset_id=asset.id,
                        attachment_type="output",
                        position=position,
                    ),
                ]
            )
        noun = "image" if len(provider_images) == 1 else "images"
        verb = "Edited" if editing else "Generated"
        assistant_message.content = f"{verb} {len(provider_images)} {noun}."
        assistant_message.status = "completed"
        operation.status = "completed"
        operation.finished_at = datetime.now(UTC)
        conversation.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(operation)
        return operation
    except (ImageValidationError, ModelEndpointError) as error:
        for storage_key in created_storage_keys:
            store.delete(storage_key)
        operation.status = "failed"
        operation.error_code = getattr(error, "code", "image_validation_failed")
        operation.error_message = str(getattr(error, "message", error))[:500]
        operation.finished_at = datetime.now(UTC)
        assistant_message.status = "failed"
        assistant_message.error_message = operation.error_message
        conversation.updated_at = datetime.now(UTC)
        await session.commit()
        raise
    except Exception as error:
        for storage_key in created_storage_keys:
            store.delete(storage_key)
        operation.status = "failed"
        operation.error_code = "image_operation_failed"
        operation.error_message = str(error)[:500]
        operation.finished_at = datetime.now(UTC)
        assistant_message.status = "failed"
        assistant_message.error_message = operation.error_message
        conversation.updated_at = datetime.now(UTC)
        await session.commit()
        raise


async def recover_interrupted_image_operations(session: AsyncSession) -> int:
    operations = list(
        await session.scalars(select(ImageOperation).where(ImageOperation.status == "running"))
    )
    if not operations:
        return 0
    now = datetime.now(UTC)
    message_ids: list[UUID] = []
    for operation in operations:
        operation.status = "failed"
        operation.error_code = "interrupted"
        operation.error_message = "Image generation was interrupted by an application restart."
        operation.finished_at = now
        message_ids.append(operation.assistant_message_id)
    messages = list(
        await session.scalars(select(ChatMessage).where(ChatMessage.id.in_(message_ids)))
    )
    for message in messages:
        if message.status == "streaming":
            message.status = "failed"
            message.error_message = "Image generation was interrupted by an application restart."
    await session.commit()
    return len(operations)


async def delete_asset_if_unreferenced(
    session: AsyncSession,
    *,
    asset: MediaAsset,
    store: PrivateMediaStore,
) -> None:
    references = 0
    references += int(
        await session.scalar(
            select(func.count(ImageOperationInput.asset_id)).where(
                ImageOperationInput.asset_id == asset.id
            )
        )
        or 0
    )
    references += int(
        await session.scalar(
            select(func.count(ImageOperationOutput.asset_id)).where(
                ImageOperationOutput.asset_id == asset.id
            )
        )
        or 0
    )
    references += int(
        await session.scalar(
            select(func.count(MessageAttachment.asset_id)).where(
                MessageAttachment.asset_id == asset.id
            )
        )
        or 0
    )
    if references:
        raise ImageValidationError("The image is still referenced by a conversation or operation.")
    storage_key = asset.storage_key
    await session.delete(asset)
    await session.commit()
    store.delete(storage_key)
