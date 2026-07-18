import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


class CommunicationStorageError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StoredCommunicationAttachment:
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    storage_key: str


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._ -]+")


def safe_filename(value: str) -> str:
    normalized = _SAFE_FILENAME.sub("_", Path(value).name).strip(" ._")
    return normalized[:240] or "attachment"


class CommunicationAttachmentStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root).expanduser().resolve()

    def write(
        self,
        *,
        account_id: str,
        message_id: str,
        filename: str,
        media_type: str,
        data: bytes,
        max_bytes: int,
    ) -> StoredCommunicationAttachment:
        if not data:
            raise CommunicationStorageError("The attachment is empty.")
        if len(data) > max_bytes:
            raise CommunicationStorageError(
                f"The attachment exceeds the {max_bytes:,}-byte limit."
            )
        clean_name = safe_filename(filename)
        storage_key = (
            f"communications/{account_id}/{message_id}/{uuid4().hex}-{clean_name}"
        )
        destination = self._path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f"{destination.suffix}.tmp-{uuid4().hex}")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return StoredCommunicationAttachment(
            filename=clean_name,
            media_type=media_type or "application/octet-stream",
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            storage_key=storage_key,
        )

    def read(self, storage_key: str) -> bytes:
        try:
            return self._path(storage_key).read_bytes()
        except FileNotFoundError as error:
            raise CommunicationStorageError("The stored attachment is missing.") from error

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)

    def _path(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if candidate == self.root or self.root not in candidate.parents:
            raise CommunicationStorageError("The attachment storage key is invalid.")
        return candidate
