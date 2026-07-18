# Aster Project Charter

Status: Accepted through Stage 15

## Product vision

Aster is a self-hosted AI workspace that lets one owner choose the assistant identity, connect model and integration services through provider-neutral contracts, control the private context available to each conversation, and run bounded unattended work with complete history.

The project starts from a focused chat product. It grows into a broader assistant platform only when each additional capability is deliberately approved, bounded, and validated.

## Product principles

### User-owned identity and context

The assistant persona is configured by the owner. No personal identity, relationship, private endpoint, memory, document, integration, or provider-specific configuration is embedded in source code, examples, tests, or public documentation.

Persona instructions are persistent application configuration. They are composed into the model instruction layer and are never represented as an ordinary user chat message.

Approved memory and private knowledge are explicit application data. The owner can inspect, edit, disable, scope, export, or delete them. Model-generated suggestions never become memory without approval.

Automation personas are frozen when the automation is saved. Later edits to the persona library do not silently rewrite unattended work.

### Correct message and execution roles

The canonical conversation model preserves the semantic difference between system, developer, user, assistant, and tool messages where supported.

A provider adapter may transform roles only when required by the target API. It must not silently merge persona instructions, tool results, memory, retrieved documents, or automation trigger data into unrelated user content.

Automation trigger payloads are untrusted data. They cannot promote themselves into platform, persona, or owner instructions.

### Provider-neutral integration

OpenAI-compatible APIs are the preferred model, image, and embedding integration contracts. MCP is the preferred interactive external-tool contract. SMTP, CalDAV, and HTTP webhooks are the initial unattended delivery contracts.

Application behavior is selected through declared capabilities and protocol contracts rather than hard-coded provider names.

### Small, stable increments

Each stage must solve a bounded set of problems reliably. Future architecture should remain possible, but speculative features are not implemented before they are needed.

One stage uses one branch and one pull request. The pull request remains draft until automated validation and real deployment testing pass.

### Observable behavior

Failures must be explicit. Endpoint errors, unavailable models, interrupted streams, stale model caches, authentication failures, denied tool calls, missing tools, execution failures, failed document extraction, unavailable embeddings, retrieval scope, image failures, automation attempts, lease recovery, and integration deliveries must be visible without exposing secrets.

### Workspace clarity

Aster is a daily-use workspace, not a collection of disconnected forms. Navigation, hierarchy, density, interaction states, and responsive behavior must remain consistent across chat, images, automations, configuration, authentication, security, tools, memory, and knowledge screens.

Visual design should clarify product state before adding decoration. New screens reuse the shared interface foundation unless a documented product requirement demands a different interaction model.

### Content, tool, retrieval, media, and trigger safety

Conversation content, tool results, memory, retrieved document text, image input, provider media, and automation trigger payloads are untrusted input.

Markdown rendering must not enable raw HTML, executable scripts, or unsafe URL handling. Uploaded and generated images must pass bounded format and structure validation before persistence or provider submission.

A model may request an interactive tool, but Aster owns discovery, enablement, conversation scope, confirmation, execution, persistence, limits, and errors. Credentials are never included in model context.

Memory and document context may provide facts but cannot override the owner, platform rules, the active persona, or the current request. Commands and role changes found inside retrieved content remain data.

Automation trigger data may inform a saved instruction but cannot rewrite it. Unattended Stage 15 runs do not execute MCP tools.

Conversation, persona, memory, retrieval, and media transfer formats are versioned, validated, bounded, and imported through authenticated application APIs.

### Predictable model routing

Generation settings are explicit and model-scoped. Unset values preserve provider defaults.

Fallback improves availability without hiding credential or request errors. Aster must never combine partial output from different models in one response. Tool-call output also counts as emitted output and prevents fallback.

Embeddings are optional. Their failure reduces semantic retrieval quality but does not disable lexical retrieval or make indexed documents unavailable.

An automation may pin an explicit model. Otherwise it uses the Primary model and normal fallback chain. The actual provider model remains persisted on the run.

### Bounded unattended execution

PostgreSQL is the durable automation queue and scheduler state. Redis, Celery, RabbitMQ, and a separate queue service are not required in the default stack.

Every automation run is persisted before execution. Queued work is claimed transactionally with an expiring lease. Heartbeat renewal proves ownership while the run is active. A worker that loses its lease stops local execution.

Model generation may retry within explicit limits. Automatic retry stops before external delivery begins so SMTP, CalDAV, and outbound-webhook side effects are not silently repeated.

Returning from downtime creates at most one catch-up run for each overdue automation before advancing to its next future occurrence.

## Implemented capabilities

### Chat

- Create, rename, search, import, export, and delete conversations
- Persist conversation history
- Stream assistant responses
- Edit and resend user messages
- Regenerate assistant responses
- Stop active responses while preserving partial output
- Select an available chat model
- Preserve canonical message roles
- Present actionable endpoint and streaming errors
- Render safe Markdown, GFM structures, tables, and fenced code
- Copy complete messages and individual code blocks
- Export conversations as Markdown or versioned Aster JSON
- Import validated Aster JSON exports
- Display tool activity, retrieval provenance, and image attachments inside the relevant turn

### Personas

- Maintain a reusable persona library
- Create, edit, duplicate, delete, import, and export personas
- Enable or disable personas
- Store names, descriptions, instructions, and system or developer placement
- Select one optional default persona for new conversations
- Freeze persona configuration into each conversation
- Freeze selected persona configuration into each automation
- Reassign or clear the persona used by future chat responses
- Preserve old conversation and automation snapshots after the source persona changes or is deleted

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
- Select Primary, Utility, Image, and optional Embedding model roles
- Resolve Utility to Primary when Utility is not configured

### Model profiles and routing

- Store optional generation settings for each cached model
- Preserve provider defaults when a setting is not configured
- Configure output-token field compatibility per model
- Declare chat and streaming capabilities
- Apply temperature, top-p, output limits, and reasoning effort
- Configure one ordered global chat fallback chain
- Skip unavailable, disabled, or incompatible fallback targets
- Fall back only before the first content or tool-call delta
- Keep authentication and request-validation failures visible
- Preserve the actual provider model identifier on assistant messages and automation runs

Dynamic cost-aware or latency-aware routing and conversation-scoped fallback chains are deferred.

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

MCP resources, prompts, sampling, elicitation, OAuth flows, server-initiated features, background tool execution, and autonomous agents are deferred.

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
- Add semantic scoring through an optional OpenAI-compatible embedding model
- Store vectors as JSON arrays in PostgreSQL without requiring pgvector
- Ignore vectors created by a different embedding model until reindexing
- Enable or disable memory and RAG independently per conversation
- Assign an explicit collection set to each conversation
- Treat memory and retrieved documents as untrusted developer context
- Persist the exact memory and chunks selected for every assistant response
- Show `[M#]` and `[D#]` provenance in chat
- Preserve retrieval flags and local collection names in conversation transfer version 4

Automatic memory acceptance, background ingestion, OCR, web crawling, autonomous knowledge maintenance, and public file hosting are deferred.

### Images

- Declare image generation, editing, multiple-input, and mask capabilities per cached model
- Select a dedicated Image model or use Primary only when it declares the required capability
- Configure normalized image defaults and bounded provider-specific parameters
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

Generic multimodal chat, image understanding by the Primary model, video, audio, OCR, SVG, public sharing, canvas editing, and background image jobs are deferred.

### Automations and integrations

- Create, edit, enable, disable, run, and delete durable automations
- Schedule one-time, fixed-interval, daily, and weekly execution with IANA timezones
- Trigger automations through authenticated-by-secret inbound webhooks
- Pin an explicit model or use the Primary fallback chain
- Freeze an optional persona snapshot into the automation
- Persist every queued, running, delivering, completed, failed, and cancelled run
- Preserve instruction snapshots, trigger payloads, actual models, outputs, errors, attempts, leases, and timestamps
- Claim work transactionally with `FOR UPDATE SKIP LOCKED` where supported
- Renew expiring leases through worker heartbeat
- Recover interrupted work after worker or database restart
- Create at most one catch-up run after downtime
- Configure bounded model retries and execution timeouts
- Stop automatic retry before external side effects begin
- Create private success and failure notifications
- Mark notifications read or delete them
- Configure SMTP integrations and send result email
- Configure CalDAV integrations and create stable iCalendar events
- Configure outbound HTTP webhooks with encrypted private headers
- Test integrations explicitly without exposing credentials
- Protect inbound webhooks with a one-time-disclosed secret header whose hash is stored
- Deduplicate caller-identified webhook deliveries
- Inspect every external delivery attempt independently
- Manage definitions, integrations, run history, and notifications through one Automations workspace

Visual workflow graphs, arbitrary conditional chains, unattended MCP tools, browser automation, inbound email polling, full calendar synchronization, OAuth provider catalogs, SMS, chat-network integrations, and distributed worker fleets are deferred.

### Authentication

- Create one owner through first-access setup
- Close public sign-up permanently after the owner exists
- Hash passwords with Argon2id
- Store opaque sessions as token hashes
- Require authentication for application data, settings, gallery, media content, automations, integrations, run history, and notifications
- Change the owner password and revoke sessions
- Recover access through an administrative container command

Inbound webhook routes are public by necessity but require a high-entropy secret header and reveal neither automation existence nor token validity beyond the shared not-found response.

### Interface and UX

- Use one consistent workspace navigation model
- Keep chat optimized for long-running desktop use
- Share typography, spacing, surfaces, status colors, and focus states
- Make selected conversations, automations, and active settings unambiguous
- Keep high-volume model and history lists bounded
- Display tool requests, approval state, execution results, failures, memories, documents, retrieval sources, image attachments, automation runs, deliveries, and notifications in context
- Provide authenticated Images and Automations workspaces

Application-wide mobile and narrow-screen remediation is deferred to a dedicated stage instead of being patched screen by screen.

## Current non-goals

- Agents or autonomous execution
- Web research and crawling
- Arbitrary conditional or multi-step workflow graphs
- Unattended MCP tool execution
- Browser automation
- Inbound email polling or mailbox synchronization
- Full calendar synchronization, event modification, or deletion
- OAuth provider catalogs
- Generic multimodal chat or visual understanding
- Audio and video features
- Public image sharing or media hosting
- Background image generation or image queues
- Multiple users, invitations, roles, and per-user data isolation
- Email-based password recovery
- Automatic persona synchronization or full persona revision history
- Dynamic, cost-aware, latency-aware, or conversation-scoped model routing
- MCP resources, prompts, sampling, elicitation, OAuth, and server-initiated features
- Automatic memory acceptance or autonomous memory maintenance
- Background document ingestion, OCR, and external knowledge crawling
- Detailed usage analytics and billing
- Application-wide mobile shell remediation

## Model roles

Aster recognizes four configuration roles:

1. Primary: chat, reasoning, interactive model-requested tools, and default automation generation
2. Utility: inexpensive bounded support work such as memory-candidate extraction
3. Image: image generation and editing
4. Embedding: optional semantic indexing and retrieval

Only Primary is required for chat and automations. Utility falls back to Primary. Image may fall back to Primary only when that model declares the required image capability. Memory and RAG remain functional with lexical retrieval when no Embedding role is configured.

## Operating mode

Aster is a single-owner, self-hosted application. The owner is created in the browser on first access. After that transaction succeeds, the setup route cannot create another account.

Remote deployment must use HTTPS through a trusted reverse proxy or tunnel. Only the web service is published; it proxies private API traffic and inbound webhooks internally so the host-only session cookie remains on one public origin.

PostgreSQL stores structured application state, automation queue state, encrypted integration credentials, and audit history. Private image bytes use a separate persistent media volume. A complete restore containing images requires both the database and media backup.

Multiple users, password recovery by email, invitations, and user-level data isolation remain deferred.

## Definition of stable

Aster is stable only when:

- Container restarts preserve conversations, configuration, persona snapshots, tool history, approved memory, knowledge collections, retrieval provenance, image history, private media, automation definitions, run history, notifications, and integrations
- Endpoint and integration changes do not require source-code edits
- Persona instructions reach chat and automation models in the intended instruction role
- Streaming does not duplicate or silently truncate messages
- Incomplete streamed Markdown remains readable
- Raw HTML is not executed from conversation content
- Conversation imports reject unsupported formats and active stream states
- Portable exports do not imply that omitted private media or automation data was transferred
- Remote API and integration failures produce clear user-facing errors
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
- Fallback never combines output from different chat or automation models
- Authentication and request-validation failures do not trigger fallback
- A tool cannot run unless it is enabled, available, and assigned to the conversation
- New tools remain disabled and confirmation-protected by default
- Pending confirmations block competing conversation branches
- Tool denials, failures, and interruptions remain explicit
- MCP credentials never appear in model context, API responses, logs, fixtures, or exports
- Tool loops and payloads remain within configured limits
- Generated memory suggestions never become approved memory automatically
- Persona-scoped memories do not leak into another persona
- Retrieved text and webhook payloads cannot promote themselves to instruction authority
- Every retrieval source and automation delivery remains inspectable
- Embedding failures preserve lexical retrieval
- Upload, extraction, chunk, source, context, image, webhook, output, and provider payload sizes remain within configured limits
- Conversation retrieval scope cannot change during generation or pending tool approval
- Scheduled occurrences and caller-identified webhook deliveries do not create duplicate runs
- A worker cannot continue after losing its run lease
- Interrupted pre-delivery runs are recovered or fail explicitly
- Automatic retries never repeat external delivery side effects
- Downtime does not produce an unbounded backlog replay
- Integration credentials and inbound webhook tokens never appear in API responses or ordinary access-log paths
- First sign-up cannot create more than one owner
- Private routes reject unauthenticated requests
- Password changes revoke existing sessions
- Desktop navigation remains usable
- Keyboard focus states remain visible
- A clean Docker Compose installation is reproducible
- Database upgrades preserve existing data
- Required lint, type checks, builds, tests, and full-stack contracts pass

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
- Scheduled automations, notifications, and external integrations: implemented in Stage 15

## Change control

Any proposed capability outside this charter must be assigned to a later stage before implementation. Keeping an extension point in the architecture is acceptable; implementing a deferred feature is not.
