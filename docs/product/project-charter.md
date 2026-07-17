# Aster Project Charter

Status: Accepted through Stage 10

## Product vision

Aster is a self-hosted AI chat application that lets a person choose the assistant identity and connect the application to model services through OpenAI-compatible APIs.

The project starts as a focused chat product. It may grow into a broader assistant platform only after the first MVP is stable and the additional scope is deliberately approved.

## Product principles

### User-owned identity

The assistant persona is configured by the user. No personal identity, relationship, private endpoint, or provider-specific configuration is embedded in the source code, examples, tests, or public documentation.

Persona instructions are persistent application configuration. They are composed into the model instruction layer and are never represented as an ordinary user chat message.

### Correct message roles

The canonical conversation model preserves the semantic difference between system, developer, user, assistant, and tool messages where supported.

A provider adapter may transform roles only when required by the target API. It must not silently merge persona instructions into user content.

### Provider-neutral integration

OpenAI-compatible APIs are the preferred integration contract. Application behavior is selected through declared capabilities and API formats rather than hard-coded provider names.

### Small, stable MVP

The MVP must solve a small set of problems reliably. Future architecture should remain possible, but speculative features are not implemented before they are needed.

### Observable behavior

Failures must be explicit. Endpoint errors, unavailable models, interrupted streams, stale model caches, and authentication failures must be visible to the user without exposing secrets.

### Workspace clarity

Aster is a daily-use workspace, not a collection of disconnected forms. Navigation, hierarchy, density, interaction states, and responsive behavior must remain consistent across chat, configuration, authentication, and security screens.

Visual design should clarify product state before adding decoration. New screens reuse the shared interface foundation unless a documented product requirement demands a different interaction model.

### Content safety

Conversation content is treated as untrusted input. Markdown rendering must not enable raw HTML, executable scripts, or unsafe URL handling.

Conversation transfer formats are versioned, validated, bounded, and imported through authenticated application APIs.

### Predictable model routing

Generation settings are explicit and model-scoped. Unset values preserve provider defaults.

Fallback improves availability without hiding credential or request errors. Aster must never combine partial output from different models in one response.

## MVP 1 capabilities

### Chat

- Create, rename, and delete conversations
- Persist conversation history
- Stream assistant responses
- Edit and resend user messages
- Regenerate assistant responses
- Select an available chat model
- Preserve canonical message roles
- Present actionable endpoint and streaming errors
- Render safe Markdown, GFM structures, and fenced code
- Copy complete messages and individual code blocks
- Search conversation titles and message content
- Export conversations as Markdown or versioned Aster JSON
- Import validated Aster JSON exports

### Persona

- Configure one global persona in settings
- Enable or disable the persona
- Store a persona name and free-form instructions
- Apply persona changes to subsequent model requests
- Keep persona configuration separate from chat history

Multiple personas, persona versioning, and per-conversation personas are deferred.

### Endpoint and model configuration

- Register multiple OpenAI-compatible endpoints
- Store a display name, base URL, and optional API credential
- Encrypt credentials before storing them
- Test endpoint connectivity
- Select a primary model
- Optionally select utility and image models
- Fall back from utility to primary when utility is not configured
- Keep image generation disabled when no image model is configured

### Model cache

- Fetch the model catalog from a compatible models endpoint
- Cache model identifiers locally
- Refresh the cache manually
- Display the last successful refresh time
- Preserve cached entries when the remote endpoint is unavailable
- Allow manual model identifiers when model listing is unsupported or incomplete
- Mark models missing from the latest refresh instead of deleting them silently

### Model profiles and routing

- Store optional generation settings for each cached model
- Preserve provider defaults when a setting is not configured
- Configure output-token field compatibility per model
- Declare chat and streaming capabilities
- Apply temperature, top-p, output limits, and reasoning effort to chat requests
- Configure one ordered global chat fallback chain
- Skip unavailable, disabled, or incompatible fallback targets at runtime
- Fall back only before the first response token
- Keep authentication and request-validation failures visible
- Preserve the actual provider model identifier on assistant messages

Dynamic routing, automatic cost or latency decisions, and conversation-scoped fallback chains are deferred.

### Authentication

- Create one owner through first-access setup
- Close public sign-up permanently after the owner exists
- Hash passwords with Argon2id
- Store opaque sessions as token hashes
- Require authentication for application data and settings
- Change the owner password and revoke sessions
- Recover access through an administrative container command

### Interface and UX

- Use one consistent workspace navigation model
- Keep chat optimized for long-running desktop use
- Share typography, spacing, surfaces, status colors, and focus states
- Make selected conversations and active settings unambiguous
- Keep high-volume model lists bounded and searchable
- Avoid external UI dependencies for the Stage 8 foundation

Application-wide mobile and narrow-screen remediation is deferred to a dedicated stage instead of being patched screen by screen.

## Current non-goals

- Agents or autonomous execution
- Tool calling and MCP
- Long-term memory
- RAG and document indexing
- Web research
- Scheduled or conditional tasks
- Email and calendar integrations
- Audio features
- Multiple users, invitations, roles, and per-user data isolation
- Email-based password recovery
- Multiple, versioned, or conversation-scoped personas
- Dynamic, cost-aware, latency-aware, or conversation-scoped model routing
- Image-generation or image-editing interface
- Detailed usage analytics and billing
- Application-wide mobile shell remediation in Stage 10

## Initial model roles

Aster recognizes three configuration roles:

1. Primary: chat and general reasoning
2. Utility: inexpensive background work in later milestones
3. Image: image operations in later milestones

Only the primary role is required to use the initial chat. The utility and image roles are configuration foundations and must not justify premature background or image features.

## Operating mode

Aster is a single-owner, self-hosted application. The owner is created in the browser on first access. After that transaction succeeds, the setup route cannot create another account.

Remote deployment must use HTTPS through a trusted reverse proxy or tunnel. Only the web service is published; it proxies API traffic internally so the host-only session cookie remains on one public origin.

Multiple users, password recovery by email, invitations, and user-level data isolation remain deferred.

## Definition of stable

Aster is stable only when:

- Container restarts preserve conversations and configuration
- Endpoint changes do not require source-code edits
- Persona instructions reach the model in the intended instruction role
- Streaming does not duplicate or silently truncate messages
- Incomplete streamed Markdown remains readable
- Raw HTML is not executed from conversation content
- Conversation imports reject unsupported formats and active stream states
- Remote API failures produce clear user-facing errors
- Cached models remain usable while an endpoint is temporarily unavailable
- Model profiles omit unset provider parameters
- Fallback never combines output from different models
- Authentication and request-validation failures do not trigger fallback
- Credentials and session tokens never appear in logs or API responses
- First sign-up cannot create more than one owner
- Private routes reject unauthenticated requests
- Password changes revoke existing sessions
- Desktop navigation remains usable
- Keyboard focus states remain visible
- A clean Docker Compose installation is reproducible
- Database migrations work against an empty database
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

## Change control

Any proposed capability outside this charter must be assigned to a later milestone before implementation. Keeping an extension point in the architecture is acceptable; implementing the deferred feature is not.
