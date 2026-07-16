# ADR-0009: Chat content rendering and conversation transfer

## Status

Accepted for Stage 9.

## Context

The initial chat preserved streamed text exactly but displayed every message as plain text. This made technical answers, code, tables, task lists, and structured explanations difficult to scan and use.

Conversation history also lacked full-content search and a supported way to move a conversation between Aster installations or save a readable offline copy.

## Decision

Aster renders user and assistant content with a safe Markdown pipeline:

- raw HTML remains disabled;
- CommonMark is extended with GFM structures and authored line breaks;
- fenced code uses declared-language syntax highlighting;
- code blocks and complete messages expose explicit copy controls;
- incomplete fenced blocks are closed only in the temporary rendered stream view;
- persisted message content is never rewritten by the renderer.

Conversation search is performed by the authenticated API across titles and message content. The sidebar debounces requests and keeps ordinary conversation ordering unchanged.

Conversation transfer uses two outputs:

- Markdown for a readable human archive;
- versioned `aster-conversation` JSON for round-trip import.

Imported JSON is authenticated, strict, and bounded. Unknown fields, unsupported versions, streaming states, invalid role metadata, excessive message counts, and excessive total content are rejected before persistence. Import creates one conversation and its messages in one database transaction.

## Consequences

- Rendering libraries become intentional frontend dependencies and must remain compatible with the supported Node and React versions.
- Raw HTML support must not be added without a separate security decision and sanitizer review.
- Export actions remain unavailable while a response is streaming.
- Aster JSON may evolve through explicit format versions rather than silently changing the existing schema.
- Search correctness is covered at the API layer; visual search behavior remains a frontend concern.
- Conversation transfer does not include credentials, endpoint configuration, persona instructions, sessions, or internal database identifiers.
