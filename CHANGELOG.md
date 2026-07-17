# Changelog

All notable changes to Aster are documented in this file.

## [Unreleased]

### Added

- Approved personal memory with global or persona scope, editing, disabling, deletion, import, export, and reindexing.
- Utility-model memory suggestions that remain pending until the owner accepts or rejects them.
- Optional OpenAI-compatible embedding-model selection for memory and document retrieval.
- Private knowledge collections with bounded text, Markdown, JSON, CSV, XML, YAML, TOML, HTML, log, and PDF ingestion.
- Deterministic document extraction, chunking, lexical indexing, optional embeddings, reindexing, and deletion.
- Explicit memory, RAG, and collection controls for individual conversations.
- Persisted retrieval provenance for every assistant response that used memory or document context.
- Visible `[M#]` and `[D#]` source cards in chat.
- Version 4 conversation transfer with portable retrieval flags and collection names.
- Memory & Knowledge settings for approved memory, suggestions, embeddings, collections, documents, and conversation scope.
- Bounded runtime configuration for memory candidates, sources, context, uploads, extraction, chunks, and embedding batches.
- MCP server configuration for Streamable HTTP and opt-in stdio transports.
- Encrypted MCP HTTP headers and process environment values.
- MCP tool discovery, synchronization, availability tracking, and stable namespaced tool identifiers.
- Global tool policies for enablement, new-conversation defaults, and confirmation requirements.
- Explicit per-conversation tool scopes.
- Native OpenAI-compatible streamed tool calling with persisted assistant calls and tool-role results.
- Owner approval and denial flows for sensitive tool calls.
- Tool execution history with arguments, status, results, errors, and timestamps.
- Bounded tool rounds, argument sizes, result sizes, and execution timeouts.
- Restart recovery for interrupted tool executions.
- Version 3 conversation transfer with portable tool-call and tool-result history.
- Tools settings and in-chat request, result, approval, and denial interfaces.
- Reusable persona library with create, edit, duplicate, delete, import, and export workflows.
- Optional default persona for new conversations.
- Frozen persona snapshots for individual conversations.
- Explicit conversation reassignment and a no-persona option for future responses.
- Persona-aware version 2 conversation exports with backward-compatible version 1 imports.
- Per-model generation profiles for context metadata, output limits, sampling, reasoning effort, and declared chat capabilities.
- Ordered global fallback routing for chat models and endpoints.
- Profile and fallback controls in Models settings.
- Safe Markdown rendering for user and assistant messages.
- GFM tables, task lists, autolinks, strikethrough, and authored line breaks.
- Fenced-code syntax highlighting with per-block copy controls.
- Message copy actions and stable rendering for incomplete streamed code fences.
- Full-history search across conversation titles and message content.
- Versioned JSON conversation export and authenticated import.
- Human-readable Markdown conversation export.
- Inline conversation renaming and keyboard access to history search.
- Shared application frame for chat, model, persona, and account navigation.
- Internal interface icon set and dedicated Aster brand mark.
- Responsive workspace navigation for desktop and mobile layouts.
- Single-owner authentication with first-access setup.
- Argon2id password hashing.
- Opaque server-side sessions stored as token hashes.
- Login rate limiting, session revocation, and password rotation.
- Administrative password reset through `python -m app.cli reset-password`.
- Account settings for password changes, logout, and revoking other sessions.
- Same-origin browser API proxy through the Next.js web service.
- External PostgreSQL support through `DATABASE_URL`.
- Optional bundled PostgreSQL through the `local-db` Compose profile.
- Runtime configuration for endpoint and stream timeouts.
- Search, availability filtering, and bounded rendering for large model caches.
- Searchable primary, utility, and image model selectors.

### Changed

- Memory and retrieved document text enter model context as explicitly untrusted developer data instead of system authority.
- Lexical retrieval remains available when no embedding model is configured or the embedding endpoint fails.
- Knowledge collections marked as defaults apply only to new conversations and are never assigned retroactively.
- Conversation exports carry retrieval intent without embedding private memory, document text, chunks, or vectors.
- Tool results are treated as untrusted data when returned to the model.
- New MCP tools start disabled, are not assigned to new conversations, and require confirmation.
- Conversation changes are blocked while a tool approval is pending.
- Changing an MCP transport removes secrets that belong to the previous transport.
- The original global persona is migrated into the persona library without discarding its instructions.
- Chat generation now reads persona context from the conversation snapshot instead of mutable global configuration.
- Editing or deleting a library persona no longer changes existing conversations.
- Unset model-profile values now preserve provider defaults and are omitted from chat requests.
- Eligible model failures may advance to the next fallback only before response content begins.
- Chat content now renders as structured documents instead of plain text.
- Conversation import validates format, version, roles, statuses, metadata, and total size.
- Interface hierarchy now derives from a neutral base, restrained accent, and shared contrast system.
- Sidebar and primary view chrome now form one continuous application frame.
- Navigation, conversation rows, controls, labels, and icons use denser shared alignment rules.
- Surface elevation and selection rely on opacity and tonal separation instead of heavy borders and shadows.
- Chat now uses a compact workspace layout with clearer conversation selection, message hierarchy, contextual actions, and a focused composer.
- Model, persona, account, setup, and sign-in screens now share one dense interface system.
- Forms, endpoint metadata, model browsing, empty states, notices, and responsive behavior use consistent tokens and interaction states.
- Every chat, model, persona, and account route now requires an authenticated owner session.
- The bundled PostgreSQL service no longer publishes port 5432 to the host.
- Endpoint discovery now allows 30 seconds by default.
- The API, web package, and release documentation use version `0.1.0` consistently.

### Fixed

- Memory suggestions work when the selected Utility or Primary model has no explicit profile.
- Persona-scoped memory cannot leak into conversations using another persona.
- Embeddings created by a different model are ignored until content is reindexed.
- Prompt-like instructions inside retrieved documents remain inside the untrusted context boundary.
- Existing conversations receive explicit retrieval settings during the Stage 13 migration without losing prior data.
- Tool names from different MCP servers cannot collide in model requests.
- A model cannot execute a tool that is disabled, unavailable, or outside the conversation scope.
- Tool execution failures and denials remain visible instead of disappearing from the model loop.
- Interrupted running tool executions are marked failed after restart.
- Persona library changes cannot retroactively rewrite the instruction context of old conversations.
- Fallback routing never combines partial output from different models.
- Authentication and request-validation failures remain visible instead of triggering fallback.
- Incomplete fenced code remains readable while a response is still streaming.
- Real endpoints that need more than ten seconds to return a large model list no longer fail prematurely.

## 0.1.0

### Added

- Persistent streamed chat through OpenAI-compatible endpoints.
- Encrypted endpoint API keys and persistent model caching.
- Primary, utility, and image model roles.
- One global persona with system or developer instruction placement.
- Persistent conversations with local title generation.
- Edit and resend with linear tail replacement.
- Assistant response regeneration.
- Explicit response stopping with partial output preservation.
- Interrupted-stream recovery and concurrent-generation protection.
