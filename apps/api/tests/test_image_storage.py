import base64
import struct
import zlib

import pytest

from app.image_storage import ImageValidationError, PrivateMediaStore, validate_and_sanitize_image


def _png_chunk(name: bytes, content: bytes) -> bytes:
    checksum = zlib.crc32(name + content).to_bytes(4, "big")
    return len(content).to_bytes(4, "big") + name + content + checksum


def _png_with_private_text() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    compressed = zlib.compress(b"\x00\x00\x00\x00\xff")
    return b"".join(
        [
            signature,
            _png_chunk(b"IHDR", header),
            _png_chunk(b"tEXt", b"GPS=private"),
            _png_chunk(b"IDAT", compressed),
            _png_chunk(b"IEND", b""),
        ]
    )


def test_png_metadata_is_removed_before_storage(tmp_path) -> None:
    validated = validate_and_sanitize_image(
        _png_with_private_text(),
        max_bytes=1_000_000,
        max_pixels=1_000_000,
    )

    assert validated.media_type == "image/png"
    assert validated.width == 1
    assert validated.height == 1
    assert b"GPS=private" not in validated.data

    store = PrivateMediaStore(str(tmp_path))
    key = store.write(validated)
    assert store.read(key) == validated.data
    store.delete(key)
    assert not (tmp_path / key).exists()


def test_invalid_and_oversized_images_are_rejected() -> None:
    with pytest.raises(ImageValidationError, match="Only PNG"):
        validate_and_sanitize_image(
            b"not-an-image",
            max_bytes=1_000,
            max_pixels=1_000,
        )

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlK7YQAAAAASUVORK5CYII="
    )
    with pytest.raises(ImageValidationError, match="byte limit"):
        validate_and_sanitize_image(png, max_bytes=10, max_pixels=1_000)
