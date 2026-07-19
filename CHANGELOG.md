# Changelog

All notable changes to Aster are documented in this file.

## [Unreleased]

### Added

- Versioned centralized model prompts, documented instruction hierarchy, explicit trust boundaries, and prompt contract tests.
- Movable, minimizable floating settings window with a compact internal menu and full-page fallback.
- Sandboxed rich email rendering with scripts, forms, navigation, and remote content blocked by default.
- Bounded AI-assisted email and Discord reply drafts that remain editable and are never sent automatically.
- Private IMAP and Discord communication accounts with encrypted credentials, explicit connection tests, and bounded background synchronization.
- Durable per-source cursors, expiring worker leases, inbound-message deduplication, and restart-safe polling.
- Persistent communication threads, messages, participants, unread state, searchable text, metadata, and private attachments.
- Manual email replies through an explicitly linked SMTP integration with threaded reply headers.
- Manual Discord replies with mention parsing permanently disabled.
- Communication-triggered automations with explicit sender, source, body, and optional Discord-mention allowlist rules.
- Private Communications workspace with Inbox, Accounts, and Rules interfaces.
- Migration `0015_communication_hub` and bounded runtime configuration for communication leases, message content, attachments, and attachment counts.
- PostgreSQL-backed one-time, interval, daily, weekly, and inbound-webhook automations.
- A dedicated worker service with transactional claiming, expiring leases, heartbeat renewal, interrupted-run recovery, and bounded retries.
- Frozen automation persona snapshots and optional explicit model selection with Primary fallback routing when no model is pinned.
- Persistent automation runs with trigger payloads, model output, attempts, errors, leases, delivery attempts, and timestamps.
- Private in-app notifications for automation success and failure with read and deletion controls.
- SMTP integration configuration, encrypted credentials, explicit connection tests, and email result delivery.
- CalDAV integration configuration, encrypted authentication, explicit connection tests, and stable iCalendar event creation.
- Inbound webhooks using a public automation UUID and one-time-disclosed `X-Aster-Webhook-Token` secret header.
- Persisted webhook delivery identifiers and idempotent duplicate handling through `X-Aster-Delivery` or `Idempotency-Key`.
- Outbound HTTP webhook integrations with encrypted private headers and structured completion payloads.
- Automation workspace with schedule, timezone, model, persona, delivery, retry, timeout, history, integration, and notification controls.
- Migration `0012_automations` and a worker health contract in Docker Compose.
- Bounded runtime configuration for polling, leases, heartbeat, scheduling batches, output size, integration timeouts, and webhook body size.
- Explicit image-model capability profiles for generation, editing, multiple inputs, masks, normalized defaults, and bounded provider parameters.
- OpenAI-compatible image generation through `/images/generations` and multipart editing through `/images/edits`.
- Explicit image mode in the chat composer with PNG, JPEG, and WebP inputs, optional masks, previews, and provider-aware parameters.
- Private media assets with signature validation, dimension limits, SHA-256 hashes, metadata removal, and atomic local storage.
- Persistent image operations with prompts, revised prompts, actual provider models, parameters, inputs, outputs, failures, and timestamps.
- Image attachments associated with the relevant user and assistant messages.
- Private Images workspace with gallery filtering, operation details, result metadata, and conversation links.
- Authenticated media content routes with private caching and content-type hardening.
- Restart recovery for interrupted image operations.
- Migration `0011_images` and the persistent `aster-media` Docker volume.
- Bounded runtime configuration for image timeouts, upload bytes, output bytes, pixels, inputs, and outputs.
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
- Shared application frame for chat, communication, image, automation, model, persona, and account navigation.
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
- Searchable primary, utility, image, and embedding model selectors.

### Changed

- Chat, title generation, memory extraction, communication drafts, automations, and agents now share a system-first reliability policy and explicit untrusted-data boundaries.
- The automation worker now also claims and synchronizes due communication accounts without adding another broker or worker service.
- Receiving a communication message persists it before any matching automation is queued.
- Communication automations require a separate enabled allowlist rule and receive bounded message snapshots as untrusted trigger data.
- The default application stack now includes a continuously running automation worker built from the API image.
- Automation model output is committed before SMTP, CalDAV, or outbound-webhook side effects begin.
- Automatic retries stop before external delivery begins so a failed delivery is recorded instead of repeated silently.
- Returning from downtime creates at most one catch-up run per overdue automation before advancing to the next future occurrence.
- Inbound webhook secrets are carried only in `X-Aster-Webhook-Token`, never in request paths that normal access logs record.
- The same-origin proxy forwards only the explicit webhook control headers required by Stage 15.
- The Image role is active and falls back to Primary only when that exact model explicitly declares the required image capability.
- Provider image URLs are downloaded immediately and never stored as durable history.
- Image media and communication attachments are stored outside PostgreSQL in a private persistent volume.
- Image turns cannot use the text edit or regeneration flows; a new image operation preserves clear lineage and parameters.
- Portable conversation exports omit private image bytes and add an explicit omission note to affected turns.
- Deleting a conversation removes its generated output files instead of leaving private media behind.
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
- Every chat, communication, image, automation, model, persona, and account route requires an authenticated owner session.
- The bundled PostgreSQL service no longer publishes port 5432 to the host.
- Endpoint discovery now allows 30 seconds by default.
- The API, web package, and release documentation use version `0.1.0` consistently.

### Fixed

- Repeated IMAP or Discord polling no longer duplicates persisted messages or communication-triggered automation runs.
- Discord replies cannot create user, role, `@everyone`, or `@here` mentions through API configuration.
- Communication attachments written before a failed database transaction are removed instead of becoming orphaned files.
- The worker and API share the same private media volume so background attachment ingestion remains available after deployment.
- Webhook delivery identifiers no longer roll back unrelated scheduler state when a duplicate is received.
- Expired automation leases are recovered, and a worker that loses ownership stops its local execution.
- The worker survives temporary database and schema unavailability during migrations instead of crashing permanently.
- Overdue interval schedules no longer replay every missed occurrence after downtime.
- Webhook secrets no longer appear in Uvicorn or ordinary reverse-proxy request paths.
- Provider failures remain visible as failed image operations and failed assistant messages without persisting partial outputs.
- Invalid base64, empty responses, oversized downloads, false media types, excessive dimensions, and unsupported image formats are rejected explicitly.
- Partially stored output files are removed when image persistence fails.
- Interrupted image operations are marked failed after restart.
- Gallery conversation links open the associated conversation instead of the most recent one.
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
