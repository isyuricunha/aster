# ADR-0004: Persistent chat and streamed completions

Status: Accepted

## Context

Aster has persistent model configuration and canonical persona composition, but it still needs a real chat path. The first chat implementation must keep conversation history in PostgreSQL, use the configured primary model, preserve canonical roles, and stream without adding a queue or provider-specific SDK.

## Decision

Aster stores conversations and linear chat messages in PostgreSQL. Stored messages contain only conversation content and delivery state; persona instructions remain in the separate global persona configuration.

Before each model request, the API loads completed conversation messages, composes the current persona, appends the new user message, and converts the canonical messages to the OpenAI-compatible chat message shape.

The upstream request uses:

```text
POST {base_url}/chat/completions
stream: true
```

The API parses upstream server-sent events and emits its own small SSE protocol to the browser:

- `meta`: persisted user and assistant message records
- `delta`: one text fragment
- `done`: the completed assistant message
- `error`: a sanitized streaming failure

The browser uses `fetch` with a readable stream because the request has a JSON body. Native `EventSource` is not used.

The configured primary model is the only model used by chat in this milestone. Conversation titles are derived locally from the first user message. Utility models are not used for title generation.

Assistant messages are created with `streaming` status before the upstream request starts. Successful responses become `completed`. Interrupted or failed responses become `failed`, retain any partial text, and store only a sanitized error message.

## Consequences

- Conversations and messages survive container restarts.
- Persona instructions remain separate from stored user messages.
- The browser receives incremental text without WebSockets or Redis.
- Upstream error bodies and API keys are not exposed through the chat API.
- Providers that reject the configured `developer` role require the persona role to be changed to `system`.
- Concurrent sends to the same conversation, branching, edit-and-resend, and regeneration are deferred to the remaining MVP work.
