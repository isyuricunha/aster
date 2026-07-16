# Aster Project Charter

Status: Accepted for MVP 1

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

Failures must be explicit. Endpoint errors, unavailable models, interrupted streams, and stale model caches must be visible to the user without exposing secrets.

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

## MVP 1 non-goals

- Agents or autonomous execution
- Tool calling and MCP
- Long-term memory
- RAG and document indexing
- Web research
- Scheduled or conditional tasks
- Email and calendar integrations
- Audio features
- Multiple users and application-managed authentication
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

## Initial operating mode

MVP 1 is a single-user, self-hosted application. Deployment-level protection may be provided by a trusted reverse proxy, private network, or another external access-control layer.

Application-managed accounts, password recovery, invitations, and multi-user data isolation are deferred.

## Definition of stable

The first MVP is stable only when:

- Container restarts preserve conversations and configuration
- Endpoint changes do not require source-code edits
- Persona instructions reach the model in the intended instruction role
- Streaming does not duplicate or silently truncate messages
- Remote API failures produce clear user-facing errors
- Cached models remain usable while an endpoint is temporarily unavailable
- Credentials never appear in logs or API responses
- A clean Docker Compose installation is reproducible
- Database migrations work against an empty database
- Required lint, type checks, builds, and tests pass

## Milestone status

- Foundation: implemented
- Endpoint and model configuration: implemented in the current milestone
- Persona composition: pending
- Chat: pending

## Change control

Any proposed capability outside this charter must be assigned to a later milestone before implementation. Keeping an extension point in the architecture is acceptable; implementing the deferred feature is not.
