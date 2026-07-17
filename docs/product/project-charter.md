# Aster Project Charter

Status: Accepted through Stage 14

## Product vision

Aster is a self-hosted AI workspace that lets one owner choose the assistant identity, connect model services and tools through provider-neutral APIs, control the private context available to each conversation, and create private visual media without surrendering durable history to provider URLs.

The project starts as a focused chat product. It may grow into a broader assistant platform only after each additional capability is deliberately approved and validated.

## Product principles

### User-owned identity, context, and media

The assistant persona is configured by the owner. No personal identity, relationship, private endpoint, memory, document, media asset, or provider-specific configuration is embedded in source code, examples, tests, or public documentation.

Persona instructions are persistent application configuration. They are composed into the model instruction layer and are never represented as an ordinary user chat message.

Approved memory and private knowledge are explicit application data. The owner can inspect, edit, disable, scope, export, or delete them. Model-generated suggestions never become memory without approval.

Private image inputs and outputs are explicit application assets. They remain associated with operations and conversations, use authenticated routes, and are never reduced to temporary provider URLs or embedded base64 inside ordinary message text.

### Correct message roles and attachments

The canonical conversation model preserves the semantic difference between system, developer, user, assistant, and tool messages where supported.

A provider adapter may transform roles only when required by the target API. It must not silently merge persona instructions, tool results, memory, or retrieved documents into user content.

Visual attachments remain separate from textual message content. An image operation creates ordinary user and assistant turns plus explicit attachment records instead of inventing a new hidden message role.

### Provider-neutral integration

OpenAI-compatible APIs are the preferred chat, embedding, and image integration contracts. MCP is the preferred external-tool contract. Application behavior is selected through declared capabilities and protocol contracts rather than hard-coded provider or model names.

### Small, stable increments

Each stage must solve a bounded set of problems reliably. Future architecture should remain possible, but speculative features are not implemented before they are needed.

One stage uses one branch and one pull request. The pull request remains draft until automated validation and real deployment testing pass.

### Observable behavior

Failures must be explicit. Endpoint errors, unavailable models, interrupted streams, stale model caches, authentication failures, denied tool calls, missing tools, execution failures, failed document extraction, unavailable embeddings, retrieval scope, invalid uploads, provider image failures, interrupted image operations, and missing media files must be visible without exposing secrets.

### Workspace clarity

Aster is a daily-use workspace, not a collection of disconnected forms. Navigation, hierarchy, density, interaction states, and responsive behavior must remain consistent across chat, images, configuration, authentication, security, tools, memory, and knowledge screens.

Visual design should clarify product state before adding decoration. New screens reuse the shared interface foundation unless a documented product requirement demands a different interaction model.

### Content, tool, retrieval, and media safety

Conversation content, tool results, memory, and retrieved document text are untrusted input. Markdown rendering must not enable raw HTML, executable scripts, or unsafe URL handling.

A model may request a tool, but Aster owns discovery, enablement, conversation scope, confirmation, execution, persistence, limits, and errors. Credentials are never included in model context.

Memory and document context may provide facts but cannot override the owner, platform rules, the active persona, or the current request. Commands and role changes found inside retrieved content remain data.

Image uploads and provider outputs are untrusted binary input. Aster owns accepted formats, validation, metadata removal, dimensions, byte limits, persistence, authenticated delivery, association, deletion, and errors.

Conversation, persona, memory, and retrieval transfer formats are versioned, validated, bounded, and imported through authenticated application APIs. Portable conversation exports never include private media bytes implicitly.

### Predictable model routing

Generation settings are explicit and model-scoped. Unset values preserve provider defaults.

Fallback improves availability without hiding credential or request errors. Aster must never combine partial output from different chat models in one response. Tool-call output also counts as emitted output and prevents fallback.

Embeddings are optional. Their failure reduces semantic retrieval quality but does not disable lexical retrieval or make indexed documents unavailable.

The Image role may fall back to Primary only when that exact model explicitly declares the required image capability. Stage 14 does not add an image fallback chain.

## Implemented capabilities

### Chat

- Create, rename, search, import, export, and delete conversations
- Persist conversation history
- Stream assistant responses
- Edit and resend textual user messages
- Regenerate textual assistant responses
- Stop active streamed responses while preserving partial output
- Select an available chat model
- Preserve canonical message roles
- Present actionable endpoint and streaming errors
- Render safe Markdown, GFM structures, tables, and fenced code
- Copy complete messages and individual code blocks
- Export conversations as Markdown or versioned Aster JSON
- Import validated Aster JSON exports
- Display tool activity, retrieval provenance, and visual attachments inside the relevant turn

### Personas

- Maintain a reusable persona library
- Create, edit, duplicate, delete, import, and export personas
- Enable or disable personas
- Store names, descriptions, instructions, and system or developer placement
- Select one optional default persona for new conversations
- Freeze persona configuration into each conversation
- Reassign or clear the persona used by future responses
- Preserve old conversation snapshots after the source persona changes or is deleted

Automatic persona synchronization and full revision history are deferred.

### Endpoint and model configuration

- Register multiple OpenAI-compatible endpoints
- Store a display name, base URL, and optional API credential
- Encrypt credentials before storing them
- Test endpoint connectivity
- Fetch and cache model catalogs
- Add model identifiers manually
- Preserve cached entries when an endpoint is unavailable
- Mark missing models unavailable instead of deleting them silently
- Select primary, utility, image, and optional embedding model roles
- Resolve utility to primary when utility is not configured
- Resolve image to primary only when the selected capability is declared explicitly

### Model profiles and routing

- Store optional chat generation settings for each cached model
- Preserve provider defaults when a setting is not configured
- Configure output-token field compatibility per model
- Declare chat and streaming capabilities
- Apply temperature, top-p, output limits, and reasoning effort
- Configure one ordered global chat fallback chain
- Skip unavailable, disabled, or incompatible chat fallback targets
- Fall back only before the first content or tool-call delta
- Keep authentication and request-validation failures visible
- Preserve the actual provider model identifier on assistant messages and image operations
- Declare image generation, editing, multiple-input, and mask capabilities independently
- Configure bounded image defaults and additional provider parameters

Dynamic routing, automatic cost or latency decisions, conversation-scoped fallback chains, and image fallback chains are deferred.

### Tools and MCP

- Configure MCP servers using Streamable HTTP
- Optionally configure stdio servers when the runtime explicitly enables local process execution
- Encrypt HTTP headers and process environment values
- Test MCP connectivity and synchronize tool catalogs
- Preserve missing tools as unavailable instead of silently deleting them
- Generate stable namespaced tool identifiers for model requests
- Enable or disable each discovered tool
- Select tools copied to new conversations by default
- Require owner confirmation per tool
- Assign an explicit tool set to each conversation
- Stream OpenAI-compatible tool calls
- Persist assistant tool calls, tool-role results, and execution audit records
- Approve or deny pending calls and resume the same model turn
- Treat tool results as untrusted data in model context
- Bound tool rounds, arguments, results, and execution duration
- Recover interrupted running executions as explicit failures
- Preserve portable tool history in conversation transfer version 3 and later

MCP resources, prompts, sampling, elicitation, OAuth flows, server-initiated features, background execution, and autonomous agents are deferred.

### Memory and retrieval

- Create, edit, disable, delete, import, export, and reindex approved memories
- Scope memory globally or to one persona
- Generate memory candidates with the Utility model without saving them automatically
- Accept, edit, or reject every generated suggestion explicitly
- Configure private knowledge collections
- Mark collections copied to new conversations by default
- Ingest bounded text, Markdown, JSON, CSV, XML, YAML, TOML, HTML, logs, and extractable PDFs
- Store extracted text, hashes, deterministic chunks, and optional embeddings
- Keep lexical retrieval available without an embedding model
- Store embeddings as JSON vectors in PostgreSQL without requiring pgvector
- Add semantic scoring through an optional OpenAI-compatible embedding model
- Ignore vectors created by a different embedding model until reindexing
- Enable or disable memory and RAG independently per conversation
- Assign an explicit collection set to each conversation
- Treat memory and retrieved documents as untrusted developer context
- Persist the exact memory and chunks selected for every assistant response
- Show `[M#]` and `[D#]` provenance in chat
- Preserve retrieval flags and local collection names in conversation transfer version 4

Automatic memory acceptance, background ingestion, OCR, web crawling, autonomous knowledge maintenance, and public file hosting are deferred.

### Images

- Select one Image model or use an explicitly compatible Primary model
- Declare generation, editing, multiple-input, and mask capabilities per cached model
- Generate images through an explicit chat composer mode
- Edit images using one or more visual inputs when supported
- Supply an optional visual mask when supported
- Accept bounded PNG, JPEG, and WebP uploads
- Validate file signatures, dimensions, byte sizes, and pixel counts
- Remove supported private metadata containers before persistence or provider submission
- Use OpenAI-compatible generation and editing routes
- Persist every operation before contacting the provider
- Accept base64 results or download provider URLs immediately
- Store durable media privately outside PostgreSQL
- Associate inputs with user turns and outputs with assistant turns
- Persist prompts, revised prompts, parameters, actual models, failures, and timestamps
- Display private attachments inside chat
- Browse the same operations and assets through an authenticated Images workspace
- Recover interrupted running operations as explicit failures after restart
- Prevent textual edit or regeneration from silently rewriting image lineage
- Make private media omission explicit in portable conversation exports

Generic multimodal chat, image understanding by the Primary model, video, audio, OCR, SVG, public sharing, canvas editing, background image jobs, scheduled generation, and provider-native non-compatible APIs are deferred.

### Authentication

- Create one owner through first-access setup
- Close public sign-up permanently after the owner exists
- Hash passwords with Argon2id
- Store opaque sessions as token hashes
- Require authentication for application data, settings, gallery, and media content
- Change the owner password and revoke sessions
- Recover access through an administrative container command

### Interface and UX

- Use one consistent workspace navigation model
- Keep chat optimized for long-running desktop use
- Share typography, spacing, surfaces, status colors, and focus states
- Make selected conversations and active settings unambiguous
- Keep high-volume model lists bounded and searchable
- Display tool requests, approval state, execution results, failures, memories, documents, retrieval sources, and image attachments in context
- Provide an Images workspace for gallery history and model capability configuration

Application-wide mobile and narrow-screen remediation is deferred to a dedicated stage instead of being patched screen by screen.

## Current non-goals

- Agents or autonomous execution
- Web research and crawling
- Scheduled or conditional tasks
- Email and calendar integrations
- Generic multimodal chat or visual understanding
- Audio and video features
- Public image sharing or media hosting
- Background image generation or image queues
- Multiple users, invitations, roles, and per-user data isolation
- Email-based password recovery
- Automatic persona synchronization or full persona revision history
- Dynamic, cost-aware, latency-aware, or conversation-scoped model routing
- MCP resources, prompts, sampling, elicitation, OAuth, and server-initiated features
- Background tool jobs or tool execution outside an active chat request
- Automatic memory acceptance or autonomous memory maintenance
- Background document ingestion, OCR, and external knowledge crawling
- Detailed usage analytics and billing
- Application-wide mobile shell remediation

## Model roles

Aster recognizes four configuration roles:

1. Primary: chat, reasoning, and model-requested tools
2. Utility: inexpensive bounded support work such as memory-candidate extraction
3. Image: image generation and editing
4. Embedding: optional semantic indexing and retrieval

Only the Primary role is required for chat. Utility falls back to Primary. Image may fall back to Primary only when that model declares the required image capability. Memory and RAG remain functional with lexical retrieval when no Embedding role is configured.

## Operating mode

Aster is a single-owner, self-hosted application. The owner is created in the browser on first access. After that transaction succeeds, the setup route cannot create another account.

Remote deployment must use HTTPS through a trusted reverse proxy or tunnel. Only the web service is published; it proxies API traffic internally so the host-only session cookie remains on one public origin.

PostgreSQL stores structured application state. Private image bytes use a separate persistent media volume. A complete restore containing images requires both the database and media backup.

Multiple users, password recovery by email, invitations, and user-level data isolation remain deferred.

## Definition of stable

Aster is stable only when:

- Container restarts preserve conversations, configuration, persona snapshots, tool history, approved memory, knowledge collections, retrieval provenance, image history, and private media
- Endpoint changes do not require source-code edits
- Persona instructions reach the model in the intended instruction role
- Streaming does not duplicate or silently truncate messages
- Incomplete streamed Markdown remains readable
- Raw HTML is not executed from conversation content
- Conversation imports reject unsupported formats and active stream states
- Portable exports do not imply that omitted private media was transferred
- Remote API failures produce clear user-facing errors
- Cached models remain usable while an endpoint is temporarily unavailable
- Chat and image profiles omit unset provider parameters
- Image capabilities are declared rather than guessed from model names
- Image-role fallback uses Primary only when it is explicitly compatible
- Provider image URLs are persisted locally before they can expire
- Invalid, oversized, unsupported, or malformed images are rejected
- Partial image outputs are removed after failed persistence
- Interrupted image operations become explicit failures after restart
- Private media routes reject unauthenticated requests
- Image turns preserve input and output association with their conversation
- Fallback never combines output from different chat models
- Authentication and request-validation failures do not trigger chat fallback
- A tool cannot run unless it is enabled, available, and assigned to the conversation
- New tools remain disabled and confirmation-protected by default
- Pending confirmations block competing conversation branches
- Tool denials, failures, and interruptions remain explicit
- MCP credentials never appear in model context, API responses, logs, fixtures, or exports
- Tool loops and payloads remain within configured limits
- Generated memory suggestions never become approved memory automatically
- Persona-scoped memories do not leak into another persona
- Retrieved text cannot promote itself to system or developer authority
- Every source used by a response remains inspectable
- Embedding failures preserve lexical retrieval
- Upload, extraction, chunk, source, context, image, and provider payload sizes remain within configured limits
- Conversation retrieval scope cannot change during generation or pending tool approval
- Credentials and session tokens never appear in logs or API responses
- First sign-up cannot create more than one owner
- Private routes reject unauthenticated requests
- Password changes revoke existing sessions
- Desktop navigation remains usable
- Keyboard focus states remain visible
- A clean Docker Compose installation is reproducible
- Database upgrades preserve existing data
- Required lint, type checks, builds, and tests pass

## Milestone status

- Foundation: implemented
- Endpoint and model configuration: implemented
- Persona composition: implemented
- Persistent chat and generation controls: implemented
- Production-ready deployment: implemented
- Single-owner authentication: implemented in Stage 7
- Interface and UX foundation: implemented in Stage 8
- Chat quality and content rendering: implemented in Stage 9
- Model profiles and fallback routing: implemented in Stage 10
- Multiple personas and conversation snapshots: implemented in Stage 11
- Tool calling and MCP: implemented in Stage 12
- Personal memory and retrieval-augmented generation: implemented in Stage 13
- Image generation, editing, private media, and gallery history: implemented in Stage 14

## Change control

Any proposed capability outside this charter must be assigned to a later stage before implementation. Keeping an extension point in the architecture is acceptable; implementing a deferred feature is not.
