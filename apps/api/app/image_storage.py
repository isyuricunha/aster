import hashlib
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


class ImageValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    data: bytes
    media_type: str
    extension: str
    width: int
    height: int
    sha256: str


_PRIVATE_PNG_CHUNKS = {b"eXIf", b"iTXt", b"tEXt", b"tIME", b"zTXt"}
_JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def _validate_dimensions(width: int, height: int, *, max_pixels: int) -> None:
    if width <= 0 or height <= 0:
        raise ImageValidationError("The image has invalid dimensions.")
    if width * height > max_pixels:
        raise ImageValidationError(f"The image exceeds the {max_pixels:,}-pixel limit.")


def _sanitize_png(data: bytes) -> tuple[bytes, int, int]:
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        raise ImageValidationError("The uploaded file is not a valid PNG image.")
    offset = len(signature)
    output = bytearray(signature)
    width = 0
    height = 0
    saw_iend = False
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        end = offset + 12 + length
        if end > len(data):
            raise ImageValidationError("The PNG image is truncated.")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        if chunk_type == b"IHDR":
            if length != 13 or width or height:
                raise ImageValidationError("The PNG image has an invalid header.")
            width, height = struct.unpack(">II", chunk_data[:8])
        if chunk_type not in _PRIVATE_PNG_CHUNKS:
            output.extend(data[offset:end])
        offset = end
        if chunk_type == b"IEND":
            saw_iend = True
            break
    if not width or not height or not saw_iend:
        raise ImageValidationError("The PNG image is incomplete.")
    return bytes(output), width, height


def _sanitize_jpeg(data: bytes) -> tuple[bytes, int, int]:
    if not data.startswith(b"\xff\xd8"):
        raise ImageValidationError("The uploaded file is not a valid JPEG image.")
    output = bytearray(data[:2])
    offset = 2
    width = 0
    height = 0
    while offset < len(data):
        if data[offset] != 0xFF:
            raise ImageValidationError("The JPEG image has an invalid marker sequence.")
        marker_start = offset
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            raise ImageValidationError("The JPEG image is truncated.")
        marker = data[offset]
        offset += 1
        if marker == 0xD9:
            output.extend(data[marker_start:offset])
            break
        if marker == 0xDA:
            if offset + 2 > len(data):
                raise ImageValidationError("The JPEG image is truncated.")
            length = struct.unpack(">H", data[offset : offset + 2])[0]
            segment_end = offset + length
            if length < 2 or segment_end > len(data):
                raise ImageValidationError("The JPEG scan header is invalid.")
            output.extend(data[marker_start:])
            offset = len(data)
            break
        if marker in {0x01, *range(0xD0, 0xD8)}:
            output.extend(data[marker_start:offset])
            continue
        if offset + 2 > len(data):
            raise ImageValidationError("The JPEG image is truncated.")
        length = struct.unpack(">H", data[offset : offset + 2])[0]
        segment_end = offset + length
        if length < 2 or segment_end > len(data):
            raise ImageValidationError("The JPEG image contains an invalid segment.")
        if marker in _JPEG_SOF_MARKERS:
            if length < 7:
                raise ImageValidationError("The JPEG frame header is invalid.")
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
        if marker not in {0xE1, 0xED, 0xFE}:
            output.extend(data[marker_start:segment_end])
        offset = segment_end
    if not width or not height:
        raise ImageValidationError("The JPEG image does not contain readable dimensions.")
    return bytes(output), width, height


def _webp_dimensions(chunk_type: bytes, chunk_data: bytes) -> tuple[int, int] | None:
    if chunk_type == b"VP8X" and len(chunk_data) >= 10:
        width = 1 + int.from_bytes(chunk_data[4:7], "little")
        height = 1 + int.from_bytes(chunk_data[7:10], "little")
        return width, height
    if chunk_type == b"VP8L" and len(chunk_data) >= 5 and chunk_data[0] == 0x2F:
        b1, b2, b3, b4 = chunk_data[1:5]
        width = 1 + b1 + ((b2 & 0x3F) << 8)
        height = 1 + ((b2 & 0xC0) >> 6) + (b3 << 2) + ((b4 & 0x0F) << 10)
        return width, height
    if chunk_type == b"VP8 " and len(chunk_data) >= 10 and chunk_data[3:6] == b"\x9d\x01\x2a":
        width = int.from_bytes(chunk_data[6:8], "little") & 0x3FFF
        height = int.from_bytes(chunk_data[8:10], "little") & 0x3FFF
        return width, height
    return None


def _sanitize_webp(data: bytes) -> tuple[bytes, int, int]:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ImageValidationError("The uploaded file is not a valid WebP image.")
    declared_size = int.from_bytes(data[4:8], "little") + 8
    if declared_size > len(data):
        raise ImageValidationError("The WebP image is truncated.")
    output_chunks = bytearray()
    offset = 12
    dimensions: tuple[int, int] | None = None
    while offset + 8 <= declared_size:
        chunk_type = data[offset : offset + 4]
        length = int.from_bytes(data[offset + 4 : offset + 8], "little")
        padded_length = length + (length % 2)
        end = offset + 8 + padded_length
        if end > declared_size:
            raise ImageValidationError("The WebP image contains an invalid chunk.")
        chunk_data = data[offset + 8 : offset + 8 + length]
        dimensions = dimensions or _webp_dimensions(chunk_type, chunk_data)
        if chunk_type not in {b"EXIF", b"XMP "}:
            output_chunks.extend(data[offset:end])
        offset = end
    if dimensions is None:
        raise ImageValidationError("The WebP image does not contain readable dimensions.")
    riff_size = 4 + len(output_chunks)
    output = b"RIFF" + riff_size.to_bytes(4, "little") + b"WEBP" + bytes(output_chunks)
    return output, dimensions[0], dimensions[1]


def validate_and_sanitize_image(
    data: bytes,
    *,
    max_bytes: int,
    max_pixels: int,
) -> ValidatedImage:
    if not data:
        raise ImageValidationError("The uploaded image is empty.")
    if len(data) > max_bytes:
        raise ImageValidationError(f"The image exceeds the {max_bytes:,}-byte limit.")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        sanitized, width, height = _sanitize_png(data)
        media_type, extension = "image/png", "png"
    elif data.startswith(b"\xff\xd8"):
        sanitized, width, height = _sanitize_jpeg(data)
        media_type, extension = "image/jpeg", "jpg"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        sanitized, width, height = _sanitize_webp(data)
        media_type, extension = "image/webp", "webp"
    else:
        raise ImageValidationError("Only PNG, JPEG, and WebP images are supported.")
    _validate_dimensions(width, height, max_pixels=max_pixels)
    if len(sanitized) > max_bytes:
        raise ImageValidationError(f"The sanitized image exceeds the {max_bytes:,}-byte limit.")
    return ValidatedImage(
        data=sanitized,
        media_type=media_type,
        extension=extension,
        width=width,
        height=height,
        sha256=hashlib.sha256(sanitized).hexdigest(),
    )


class PrivateMediaStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root).expanduser().resolve()

    def write(self, image: ValidatedImage) -> str:
        storage_key = f"assets/{uuid4().hex}.{image.extension}"
        destination = self._path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f"{destination.suffix}.tmp-{uuid4().hex}")
        try:
            temporary.write_bytes(image.data)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return storage_key

    def read(self, storage_key: str) -> bytes:
        path = self._path(storage_key)
        try:
            return path.read_bytes()
        except FileNotFoundError as error:
            raise ImageValidationError("The stored image file is missing.") from error

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)

    def _path(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if candidate == self.root or self.root not in candidate.parents:
            raise ImageValidationError("The media storage key is invalid.")
        return candidate
