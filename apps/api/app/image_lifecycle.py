from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.image_models import (
    ImageOperation,
    ImageOperationInput,
    ImageOperationOutput,
    MediaAsset,
    MessageAttachment,
)
from app.image_storage import PrivateMediaStore


async def ensure_message_has_no_image_attachments(
    session: AsyncSession,
    message_id: UUID,
) -> None:
    attachment_id = await session.scalar(
        select(MessageAttachment.asset_id)
        .where(MessageAttachment.message_id == message_id)
        .limit(1)
    )
    if attachment_id is not None:
        raise ValueError(
            "Image turns cannot use text edit or regeneration. Start a new image operation instead."
        )


async def conversation_media_candidate_ids(
    session: AsyncSession,
    conversation_id: UUID,
) -> set[UUID]:
    input_ids = set(
        await session.scalars(
            select(ImageOperationInput.asset_id)
            .join(ImageOperation, ImageOperation.id == ImageOperationInput.operation_id)
            .where(ImageOperation.conversation_id == conversation_id)
        )
    )
    output_ids = set(
        await session.scalars(
            select(ImageOperationOutput.asset_id)
            .join(ImageOperation, ImageOperation.id == ImageOperationOutput.operation_id)
            .where(ImageOperation.conversation_id == conversation_id)
        )
    )
    return input_ids | output_ids


async def delete_unreferenced_media_assets(
    session: AsyncSession,
    asset_ids: set[UUID],
) -> list[str]:
    if not asset_ids:
        return []
    assets = list(
        await session.scalars(
            select(MediaAsset).where(
                MediaAsset.id.in_(asset_ids),
                ~exists(
                    select(ImageOperationInput.asset_id).where(
                        ImageOperationInput.asset_id == MediaAsset.id
                    )
                ),
                ~exists(
                    select(ImageOperationOutput.asset_id).where(
                        ImageOperationOutput.asset_id == MediaAsset.id
                    )
                ),
                ~exists(
                    select(MessageAttachment.asset_id).where(
                        MessageAttachment.asset_id == MediaAsset.id
                    )
                ),
            )
        )
    )
    storage_keys = [asset.storage_key for asset in assets]
    for asset in assets:
        await session.delete(asset)
    await session.flush()
    return storage_keys


async def delete_conversation_output_media(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    store: PrivateMediaStore,
) -> list[str]:
    del store
    rows = (
        await session.execute(
            select(MediaAsset.id, MediaAsset.storage_key)
            .join(ImageOperationOutput, ImageOperationOutput.asset_id == MediaAsset.id)
            .join(ImageOperation, ImageOperation.id == ImageOperationOutput.operation_id)
            .where(ImageOperation.conversation_id == conversation_id)
        )
    ).all()
    if not rows:
        return []
    asset_ids = [asset_id for asset_id, _ in rows]
    storage_keys = [storage_key for _, storage_key in rows]
    await session.execute(delete(MediaAsset).where(MediaAsset.id.in_(asset_ids)))
    await session.flush()
    return storage_keys


def delete_storage_keys(store: PrivateMediaStore, storage_keys: list[str]) -> None:
    for storage_key in storage_keys:
        store.delete(storage_key)
