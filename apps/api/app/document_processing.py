import json
import re
from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePath

from pypdf import PdfReader


class DocumentProcessingError(Exception):
    pass


class _VisibleHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        elif self._ignored_depth == 0 and tag in {
            "p",
            "div",
            "section",
            "article",
            "br",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif self._ignored_depth == 0 and tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self.parts.append(data)


_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".json",
    ".jsonl",
    ".csv",
    ".tsv",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".log",
    ".html",
    ".htm",
}
_TEXT_MEDIA_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/tab-separated-values",
    "text/html",
    "application/json",
    "application/jsonl",
    "application/xml",
    "text/xml",
    "application/yaml",
    "text/yaml",
    "application/toml",
}


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentProcessingError("The document could not be decoded as text.")


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as error:
        raise DocumentProcessingError("The PDF could not be opened.") from error
    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception as error:
            raise DocumentProcessingError("Encrypted PDFs are not supported.") from error
        if not unlocked:
            raise DocumentProcessingError("Encrypted PDFs are not supported.")
    pages: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception as error:
            raise DocumentProcessingError("The PDF text could not be extracted.") from error
        if text.strip():
            pages.append(text)
    if not pages:
        raise DocumentProcessingError(
            "The PDF does not contain extractable text. Scanned PDFs require OCR outside Aster."
        )
    return "\n\n".join(pages)


def _extract_html(text: str) -> str:
    parser = _VisibleHtmlParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as error:
        raise DocumentProcessingError("The HTML document could not be parsed.") from error
    return "".join(parser.parts)


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[\t\f\v ]+", " ", line).strip() for line in text.split("\n")]
    normalized: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line
        if blank and previous_blank:
            continue
        normalized.append(line)
        previous_blank = blank
    return "\n".join(normalized).strip()


def extract_document_text(
    data: bytes,
    *,
    filename: str,
    media_type: str,
    max_characters: int,
) -> str:
    suffix = PurePath(filename).suffix.casefold()
    normalized_media_type = media_type.split(";", 1)[0].strip().casefold()
    if suffix == ".pdf" or normalized_media_type == "application/pdf":
        text = _extract_pdf(data)
    elif suffix in {".html", ".htm"} or normalized_media_type == "text/html":
        text = _extract_html(_decode_text(data))
    elif suffix in _TEXT_EXTENSIONS or normalized_media_type in _TEXT_MEDIA_TYPES:
        text = _decode_text(data)
        if suffix == ".json" or normalized_media_type == "application/json":
            try:
                parsed = json.loads(text)
                text = json.dumps(parsed, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
    else:
        raise DocumentProcessingError(
            "Unsupported document type. Use text, Markdown, JSON, CSV, XML, HTML, or PDF."
        )

    normalized = _normalize_text(text)
    if not normalized:
        raise DocumentProcessingError("The document does not contain extractable text.")
    if len(normalized) > max_characters:
        raise DocumentProcessingError(
            f"The extracted document exceeds the {max_characters:,}-character limit."
        )
    return normalized


def _preferred_cut(text: str, start: int, hard_end: int) -> int:
    if hard_end >= len(text):
        return len(text)
    lower_bound = start + max(1, (hard_end - start) // 2)
    for separator in ("\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "):
        position = text.rfind(separator, lower_bound, hard_end)
        if position >= lower_bound:
            return position + len(separator)
    return hard_end


def chunk_document(
    text: str,
    *,
    chunk_characters: int,
    overlap: int,
    max_chunks: int,
) -> list[str]:
    if chunk_characters <= 0 or overlap < 0 or overlap >= chunk_characters:
        raise ValueError("Invalid document chunk configuration")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        hard_end = min(len(text), start + chunk_characters)
        end = _preferred_cut(text, start, hard_end)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if len(chunks) > max_chunks:
            raise DocumentProcessingError(
                f"The document exceeds the {max_chunks:,}-chunk limit."
            )
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        while next_start < end and text[next_start].isspace():
            next_start += 1
        start = next_start
    return chunks
