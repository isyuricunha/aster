# Aster

Aster is a self-hosted AI chat application built around user-defined personas, OpenAI-compatible model endpoints, and controlled tool execution.

The current foundation includes single-owner authentication, persistent streamed chat, reusable personas, model profiles and fallback routing, safe Markdown rendering, conversation transfer, and MCP tools with explicit owner control.

## Current capabilities

- First-access creation of one owner account
- Argon2id password hashing and opaque server-side sessions
- Login rate limiting, password changes, logout, and session revocation
- OpenAI-compatible endpoint registration, testing, and encrypted API credentials
- Persistent model discovery and manual model entries
- Primary, utility, and image model roles
- Per-model generation profiles and one ordered chat fallback chain
- Reusable persona library with frozen conversation snapshots
- Persistent streamed conversations with edit, resend, regenerate, and stop controls
- Full-history search and versioned conversation import and export
- Safe Markdown, GFM, highlighted code blocks, and copy controls
- MCP servers over Streamable HTTP
- Opt-in local MCP servers over stdio
- Encrypted MCP HTTP headers and process environment values
- Tool discovery, synchronization, availability tracking, and namespaced model-facing names
- Global tool enablement, new-conversation defaults, and confirmation policy
- Explicit tool scope for each conversation
- Persisted assistant tool calls, tool-role results, and execution history
- Owner approval and denial for sensitive calls
- Bounded tool rounds, arguments, results, and execution timeouts
- Interrupted stream and tool-execution recovery after restart

## Explicitly out of scope

- Multiple users, invitations, roles, or per-user data isolation
- Email password recovery
- Autonomous background agents
- Long-term memory and retrieval-augmented generation
- Document indexing and built-in web research
- Schedulers, conditional tasks, and automations
- Email and calendar integrations
- Automatic persona synchronization or full persona revision history
- Dynamic cost-aware or latency-aware model routing
- Image-generation user interface
- Application-wide mobile shell remediation

## Architecture

```text
apps/web  Next.js user interface and same-origin API proxy
apps/api  FastAPI application, model adapters, MCP client, and migrations
postgres  Optional bundled PostgreSQL database
```

Docker Compose is the initial deployment target. Redis is intentionally absent because Aster does not currently require a queue or distributed state.

The public deployment exposes only the web service. Next.js proxies `/api` to FastAPI through the internal Compose network so authentication remains on one origin.

## Requirements

For the Docker deployment:

- Docker with Compose support

For local development outside containers:

- Node.js 22+
- pnpm 10+
- Python 3.13+
- uv
- PostgreSQL 17+

## Start with the bundled PostgreSQL database

Create the environment file:

```bash
cp .env.example .env
```

Generate a stable encryption key:

```bash
openssl rand -hex 32
```

Set the generated value as `ASTER_ENCRYPTION_KEY` in `.env`. Do not rotate it casually. Stored endpoint credentials and MCP secrets depend on it.

The example environment enables the bundled database:

```env
COMPOSE_PROFILES=local-db
POSTGRES_DB=aster
POSTGRES_USER=aster
POSTGRES_PASSWORD=aster
DATABASE_URL=
```

Start Aster:

```bash
docker compose up -d --build
```

PostgreSQL is stored in the `postgres-data` Docker volume and is not published to the host.

## First sign-up

Open the web service after the containers become healthy:

- Local: `http://localhost:3000`
- LAN example: `http://192.168.1.20:3000`

When no owner exists, Aster redirects to `/setup`. That transaction creates the only owner and permanently closes public sign-up.

No owner username or password belongs in `.env`.

After setup:

- unauthenticated visitors are redirected to `/login`;
- application data and settings require a valid session;
- browser sessions use an `HttpOnly` host-only cookie;
- only a SHA-256 digest of each random session token is stored.

## Use an external PostgreSQL database

Disable the bundled database profile and provide an async PostgreSQL URL:

```env
COMPOSE_PROFILES=
DATABASE_URL=postgresql+asyncpg://user:password@database-host:5432/aster
```

Then start the same stack:

```bash
docker compose up -d --build
```

Only the API and web services start when `COMPOSE_PROFILES` is empty. The API applies Alembic migrations before starting in both database modes.

## Open Aster

Default local addresses:

- Chat: `http://localhost:3000`
- Model settings: `http://localhost:3000/settings/models`
- Persona settings: `http://localhost:3000/settings/persona`
- Tools settings: `http://localhost:3000/settings/tools`
- Account settings: `http://localhost:3000/settings/account`
- API health: `http://localhost:8000/health`
- API readiness: `http://localhost:8000/ready`
- API documentation in development: `http://localhost:8000/docs`

API documentation is disabled when `APP_ENVIRONMENT=production`.

## Access Aster from another machine

Set the exact browser origin in `.env`:

```env
ASTER_CORS_ORIGINS=http://192.168.1.20:3000
ASTER_API_INTERNAL_URL=http://api:8000
ASTER_SESSION_SECURE=false
```

The browser uses the web origin for every request. It does not need the API port or a separate public API URL.

## Expose Aster through HTTPS

Publish only the web service through a trusted reverse proxy or tunnel:

```text
https://aster.example.com/ -> web:3000
```

Do not route public `/api` traffic directly to FastAPI. The Next.js proxy must keep that path on the same public origin as the session cookie.

Production environment:

```env
APP_ENVIRONMENT=production
ASTER_CORS_ORIGINS=https://aster.example.com
ASTER_API_INTERNAL_URL=http://api:8000
ASTER_SESSION_SECURE=true
```

Apply origin or cookie changes with:

```bash
docker compose up -d --force-recreate api web
```

## Authentication settings

```env
ASTER_SESSION_COOKIE_NAME=aster_session
ASTER_SESSION_SECURE=false
ASTER_SESSION_ABSOLUTE_DAYS=30
ASTER_SESSION_IDLE_HOURS=168
ASTER_SESSION_TOUCH_SECONDS=300
ASTER_LOGIN_ATTEMPTS=5
ASTER_LOGIN_WINDOW_SECONDS=300
```

Password changes revoke every existing session and create a fresh session for the current browser. Account settings can also revoke every other active session.

A forgotten password is reset from the API container:

```bash
docker compose exec api python -m app.cli reset-password
```

## OpenAI-compatible endpoints

Enter the API root as the endpoint URL. Include `/v1` when the service exposes compatible routes there.

Aster uses:

```text
GET  {base_url}/models
POST {base_url}/chat/completions
Authorization: Bearer <api-key>
```

Chat requests stream from the primary model. Profiles add only explicitly configured generation fields. Eligible failures may advance to the next fallback only before response output begins.

## Tools and MCP

Tools are configured in `/settings/tools`.

The intended workflow is:

1. Add an MCP server.
2. Test the connection.
3. Synchronize its tool catalog.
4. Review every discovered tool.
5. Enable only the tools that should be available.
6. Choose whether a tool requires confirmation.
7. Optionally assign it to new conversations by default.
8. Select the exact tools available to an existing conversation.

Discovered tools start disabled, are not assigned to new conversations, and require confirmation. A model cannot execute a tool that is disabled, unavailable, or outside the current conversation scope.

### Streamable HTTP

Use an absolute HTTP or HTTPS MCP URL. Optional headers are encrypted before storage. API responses return only saved header names, never values.

Aster does not follow redirects for MCP HTTP connections. Configure the final server URL directly.

### Stdio

Local process execution is disabled by default. Enable it only on a trusted self-hosted deployment:

```env
ASTER_MCP_STDIO_ENABLED=true
```

A stdio server stores its command, argument list, and encrypted environment values. HTTP headers and stdio environment values are transport-specific; changing transports removes secrets from the previous transport.

Enabling stdio allows Aster to start configured local processes inside the API container. Do not enable it on a host where the owner should not have that capability.

### Tool approval and history

A tool may run automatically or pause for explicit owner approval. Pending approval blocks new messages, edit-and-resend, regeneration, persona changes, and tool-scope changes in that conversation.

Every call stores:

- the assistant message and provider call ID;
- the resolved tool and arguments;
- approval state;
- result or sanitized error;
- start, finish, creation, and update timestamps.

Tool results are returned to the model as untrusted data. Failures and denials remain visible in the canonical conversation instead of disappearing from the loop.

Conversation export version 3 preserves portable assistant tool calls and tool-role results. It does not export MCP credentials, server configuration, or execution database IDs.

### Tool runtime limits

```env
ASTER_MCP_TIMEOUT_SECONDS=30
ASTER_TOOL_MAX_ROUNDS=8
ASTER_TOOL_ARGUMENT_MAX_CHARACTERS=100000
ASTER_TOOL_RESULT_MAX_CHARACTERS=100000
```

- `ASTER_MCP_TIMEOUT_SECONDS` caps each MCP connection and request.
- `ASTER_TOOL_MAX_ROUNDS` stops unbounded model-to-tool loops.
- `ASTER_TOOL_ARGUMENT_MAX_CHARACTERS` rejects oversized model arguments.
- `ASTER_TOOL_RESULT_MAX_CHARACTERS` truncates oversized results before they return to the model.

Recreate the API container after changing runtime settings:

```bash
docker compose up -d --force-recreate api
```

## Persona snapshots

One enabled persona may be selected as the default. New conversations copy that persona into a frozen snapshot. Editing or deleting the library source does not alter existing conversations.

Reassigning a conversation changes only the persona snapshot used for later model requests. Existing messages remain unchanged.

## Backup and upgrade

Back up the bundled database:

```bash
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > aster-backup.sql
```

Upgrade the source checkout without removing the database volume:

```bash
git pull --ff-only
docker compose up -d --build
```

The Stage 11 migration preserves the legacy persona as a library entry and conversation snapshot. Stage 12 adds MCP configuration, conversation tool scope, tool metadata on chat messages, and execution history without rewriting existing conversations.

Changing `ASTER_ENCRYPTION_KEY` without re-encrypting stored credentials makes endpoint and MCP secrets unreadable.

## Local checks

### Web

```bash
pnpm install
pnpm lint
pnpm typecheck
pnpm build
```

### API

```bash
export ASTER_ENCRYPTION_KEY="development-key-with-at-least-32-characters"
cd apps/api
uv sync --group dev
uv run ruff check .
uv run pytest
uv run alembic upgrade head
```

## Project documentation

- [Changelog](CHANGELOG.md)
- [Project charter](docs/product/project-charter.md)
- [ADR-0001: Initial architecture](docs/decisions/0001-initial-architecture.md)
- [ADR-0002: Model endpoints and local model cache](docs/decisions/0002-model-endpoints-and-cache.md)
- [ADR-0003: Global persona and canonical message composition](docs/decisions/0003-persona-and-message-composition.md)
- [ADR-0004: Persistent chat and streamed completions](docs/decisions/0004-persistent-chat-and-streaming.md)
- [ADR-0005: Linear chat replacement and generation lifecycle](docs/decisions/0005-chat-generation-lifecycle.md)
- [ADR-0006: Runtime deployment configuration](docs/decisions/0006-runtime-deployment-configuration.md)
- [ADR-0007: Single-owner authentication](docs/decisions/0007-single-owner-authentication.md)
- [ADR-0008: Interface foundation](docs/decisions/0008-interface-foundation.md)
- [ADR-0009: Chat content rendering and transfer](docs/decisions/0009-chat-content-and-transfer.md)
- [ADR-0010: Model profiles and fallback routing](docs/decisions/0010-model-profiles-and-fallback-routing.md)
- [ADR-0011: Persona library and conversation snapshots](docs/decisions/0011-persona-library-and-conversation-snapshots.md)
- [ADR-0012: Tools and MCP](docs/decisions/0012-tools-and-mcp.md)

## Security baseline

- Passwords are stored only as Argon2id hashes.
- Session tokens are random, stored only as hashes, and delivered through `HttpOnly` cookies.
- Unsafe browser requests validate their origin.
- API responses are marked `Cache-Control: no-store`.
- Endpoint API keys and MCP secrets are encrypted before storage and never returned by APIs.
- Upstream response bodies are not forwarded to the owner.
- Tool results are treated as untrusted content.
- New tools use deny-by-default configuration.
- The bundled PostgreSQL service is not published to the host.
- Provider behavior is implemented through generic contracts rather than hard-coded provider names.

## Status

Stages 1 through 12 have automated validation gates. Real deployment validation remains required before each stage is merged.
