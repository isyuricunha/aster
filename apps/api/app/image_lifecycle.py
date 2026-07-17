from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.image_models import (
    ImageOperation,
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


async def delete_conversation_output_media(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    store: PrivateMediaStore,
) -> list[str]:
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
