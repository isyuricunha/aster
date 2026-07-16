# Aster Project Charter

Status: Accepted through Stage 8

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
- Preserve usable navigation and controls on narrow screens
- Share typography, spacing, surfaces, status colors, and focus states
- Make selected conversations and active settings unambiguous
- Keep high-volume model lists bounded and searchable
- Avoid external UI dependencies for the Stage 8 foundation

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
- Advanced user-defined model parameters
- Intelligent model routing and fallback chains
- Image-generation or image-editing interface
- Detailed usage analytics and billing

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
- Remote API failures produce clear user-facing errors
- Cached models remain usable while an endpoint is temporarily unavailable
- Credentials and session tokens never appear in logs or API responses
- First sign-up cannot create more than one owner
- Private routes reject unauthenticated requests
- Password changes revoke existing sessions
- Desktop and narrow-screen navigation remain usable
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

## Change control

Any proposed capability outside this charter must be assigned to a later milestone before implementation. Keeping an extension point in the architecture is acceptable; implementing the deferred feature is not.
