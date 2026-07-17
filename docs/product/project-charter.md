# Aster Project Charter

Status: Accepted through Stage 12

## Product vision

Aster is a self-hosted AI chat application that lets a person choose the assistant identity and connect the application to model services and tools through provider-neutral APIs.

The project starts as a focused chat product. It may grow into a broader assistant platform only after each additional capability is deliberately approved and validated.

## Product principles

### User-owned identity

The assistant persona is configured by the user. No personal identity, relationship, private endpoint, or provider-specific configuration is embedded in the source code, examples, tests, or public documentation.

Persona instructions are persistent application configuration. They are composed into the model instruction layer and are never represented as an ordinary user chat message.

### Correct message roles

The canonical conversation model preserves the semantic difference between system, developer, user, assistant, and tool messages where supported.

A provider adapter may transform roles only when required by the target API. It must not silently merge persona instructions or tool results into user content.

### Provider-neutral integration

OpenAI-compatible APIs are the preferred model integration contract. MCP is the preferred external-tool contract. Application behavior is selected through declared capabilities and protocol contracts rather than hard-coded provider names.

### Small, stable increments

Each stage must solve a bounded set of problems reliably. Future architecture should remain possible, but speculative features are not implemented before they are needed.

One stage uses one branch and one pull request. The pull request remains draft until automated validation and real deployment testing pass.

### Observable behavior

Failures must be explicit. Endpoint errors, unavailable models, interrupted streams, stale model caches, authentication failures, denied tool calls, missing tools, and execution failures must be visible without exposing secrets.

### Workspace clarity

Aster is a daily-use workspace, not a collection of disconnected forms. Navigation, hierarchy, density, interaction states, and responsive behavior must remain consistent across chat, configuration, authentication, and security screens.

Visual design should clarify product state before adding decoration. New screens reuse the shared interface foundation unless a documented product requirement demands a different interaction model.

### Content and tool safety

Conversation content and tool results are untrusted input. Markdown rendering must not enable raw HTML, executable scripts, or unsafe URL handling.

A model may request a tool, but Aster owns discovery, enablement, conversation scope, confirmation, execution, persistence, limits, and errors. Credentials are never included in model context.

Conversation and persona transfer formats are versioned, validated, bounded, and imported through authenticated application APIs.

### Predictable model routing

Generation settings are explicit and model-scoped. Unset values preserve provider defaults.

Fallback improves availability without hiding credential or request errors. Aster must never combine partial output from different models in one response. Tool-call output also counts as emitted output and prevents fallback.

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
- Select primary, utility, and image model roles
- Resolve utility to primary when utility is not configured

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
- Preserve the actual provider model identifier on assistant messages

Dynamic routing, automatic cost or latency decisions, and conversation-scoped fallback chains are deferred.

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
- Preserve portable tool history in conversation transfer version 3

MCP resources, prompts, sampling, elicitation, OAuth flows, server-initiated features, background execution, and autonomous agents are deferred.

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
- Display tool requests, approval state, execution results, and failures in context

Application-wide mobile and narrow-screen remediation is deferred to a dedicated stage instead of being patched screen by screen.

## Current non-goals

- Agents or autonomous execution
- Long-term memory
- RAG and document indexing
- Web research
- Scheduled or conditional tasks
- Email and calendar integrations
- Audio features
- Multiple users, invitations, roles, and per-user data isolation
- Email-based password recovery
- Automatic persona synchronization or full persona revision history
- Dynamic, cost-aware, latency-aware, or conversation-scoped model routing
- MCP resources, prompts, sampling, elicitation, OAuth, and server-initiated features
- Background tool jobs or tool execution outside an active chat request
- Image-generation or image-editing interface
- Detailed usage analytics and billing
- Application-wide mobile shell remediation

## Initial model roles

Aster recognizes three configuration roles:

1. Primary: chat, reasoning, and model-requested tools
2. Utility: inexpensive background work in later milestones
3. Image: image operations in later milestones

Only the primary role is required for chat. Utility and image remain configuration foundations and do not justify premature background or image features.

## Operating mode

Aster is a single-owner, self-hosted application. The owner is created in the browser on first access. After that transaction succeeds, the setup route cannot create another account.

Remote deployment must use HTTPS through a trusted reverse proxy or tunnel. Only the web service is published; it proxies API traffic internally so the host-only session cookie remains on one public origin.

Multiple users, password recovery by email, invitations, and user-level data isolation remain deferred.

## Definition of stable

Aster is stable only when:

- Container restarts preserve conversations, configuration, persona snapshots, and tool history
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
- A tool cannot run unless it is enabled, available, and assigned to the conversation
- New tools remain disabled and confirmation-protected by default
- Pending confirmations block competing conversation branches
- Tool denials, failures, and interruptions remain explicit
- MCP credentials never appear in model context, API responses, logs, fixtures, or exports
- Tool loops and payloads remain within configured limits
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

## Change control

Any proposed capability outside this charter must be assigned to a later stage before implementation. Keeping an extension point in the architecture is acceptable; implementing a deferred feature is not.
