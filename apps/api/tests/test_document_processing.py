import pytest

from app.document_processing import (
    DocumentProcessingError,
    chunk_document,
    extract_document_text,
)


def test_text_extraction_normalizes_content() -> None:
    text = extract_document_text(
        b"Title\r\n\r\n  first   line  \r\nsecond line\x00",
        filename="notes.md",
        media_type="text/markdown",
        max_characters=10_000,
    )

    assert text == "Title\n\nfirst line\nsecond line"


def test_html_extraction_ignores_script_and_style_content() -> None:
    text = extract_document_text(
        b"<h1>Visible</h1><script>steal()</script><p>Answer</p><style>hidden</style>",
        filename="page.html",
        media_type="text/html",
        max_characters=10_000,
    )

    assert "Visible" in text
    assert "Answer" in text
    assert "steal" not in text
    assert "hidden" not in text


def test_unsupported_binary_document_is_rejected() -> None:
    with pytest.raises(DocumentProcessingError, match="Unsupported document type"):
        extract_document_text(
            b"\x89PNG",
            filename="image.png",
            media_type="image/png",
            max_characters=10_000,
        )


def test_chunking_preserves_overlap_without_exceeding_limit() -> None:
    text = " ".join(f"word-{index}" for index in range(200))

    chunks = chunk_document(
        text,
        chunk_characters=240,
        overlap=40,
        max_chunks=20,
    )

    assert 2 <= len(chunks) <= 20
    assert all(len(chunk) <= 240 for chunk in chunks)
    assert chunks[0][-20:] in chunks[1]


def test_chunking_rejects_documents_that_exceed_the_chunk_limit() -> None:
    with pytest.raises(DocumentProcessingError, match="chunk limit"):
        chunk_document(
            "x " * 10_000,
            chunk_characters=400,
            overlap=20,
            max_chunks=2,
        )
