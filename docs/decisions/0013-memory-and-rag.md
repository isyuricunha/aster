# ADR-0013: Personal memory and bounded retrieval

## Status

Accepted for Stage 13.

## Context

Aster needs durable personal context and private document retrieval without turning model output into hidden authority or requiring a second infrastructure stack for basic self-hosting.

Memory, document text, embeddings, and generated suggestions have different trust and lifecycle requirements. Treating them as one opaque prompt string would make editing, deletion, transfer, auditing, and security boundaries unreliable.

## Decision

Aster stores approved memory, pending suggestions, knowledge collections, extracted documents, chunks, conversation retrieval settings, and per-response source usage as separate records.

### Memory

- Memory is explicit application data.
- Memories may be global or scoped to one persona.
- Manual and imported memories are owner-controlled.
- Utility-model extraction creates pending suggestions only.
- Suggestions require explicit acceptance before they become memory.
- Memories can be edited, disabled, exported, imported, reindexed, or deleted.

### Documents

- Stage 13 accepts text, Markdown, JSON, CSV, XML, YAML, TOML, HTML, logs, and extractable PDFs.
- Ingestion is synchronous and bounded by bytes, extracted characters, chunk count, and chunk size.
- Aster stores extracted text, hashes, and chunks. It does not expose original uploads through a public route.
- Scanned PDFs require OCR outside Aster.
- Collections may be defaults for new conversations, but are never assigned retroactively.

### Retrieval

- Lexical retrieval is always available.
- An optional OpenAI-compatible embedding model adds semantic scoring.
- Embeddings are stored as JSON vectors in PostgreSQL to keep the default deployment independent of pgvector.
- Vectors carry the model identifier that created them. Incompatible vectors are ignored until reindexing.
- Embedding failures do not disable lexical indexing or retrieval.
- Retrieved memory and document chunks enter model context as untrusted developer data, never as system authority.
- Document-dependent claims use visible `[D#]` citation labels.
- Every selected source is persisted against the assistant message before generation begins.

### Conversation scope and transfer

- Memory and RAG can be disabled independently per conversation.
- Collection assignment is explicit per conversation.
- Scope changes are blocked during active generation and pending tool approval.
- Conversation transfer version 4 carries only retrieval flags and collection names.
- Memory records, document text, embeddings, and source snapshots are not smuggled into portable conversation JSON.

## Consequences

- Aster can explain exactly which private context affected a response.
- Deleting or disabling memory and collections affects later retrieval without rewriting old messages.
- The default stack remains FastAPI, Next.js, and PostgreSQL.
- Semantic search may be slower than a dedicated vector extension for very large libraries; Stage 13 intentionally favors simple self-hosting and bounded candidate sets.
- Background ingestion, OCR, web crawling, automatic memory acceptance, and autonomous knowledge maintenance remain deferred.
