# Aster

Aster is a self-hosted AI chat application built around user-defined personas and OpenAI-compatible model endpoints.

The focused chat foundation is complete. Stages 7 through 11 add single-owner authentication, the shared application interface, structured chat rendering, model profiles and fallback routing, and multiple reusable personas with stable conversation snapshots.

## Current capabilities

- First-access owner setup with no username or password in environment variables
- Argon2id password hashing and opaque server-side sessions
- Login rate limiting, password changes, logout, and session revocation
- Register, edit, disable, test, and delete OpenAI-compatible endpoints
- Encrypt optional Bearer API keys before storing them in PostgreSQL
- Synchronize model IDs from `GET /models`
- Preserve cached model entries when an endpoint is unavailable
- Mark discovered models missing from a later sync without deleting them
- Add model IDs manually
- Search and browse large model caches without rendering the entire list at once
- Select primary, utility, and image model roles through searchable selectors
- Configure per-model output, sampling, reasoning, and compatibility profiles
- Configure one ordered global fallback chain without combining partial model output
- Maintain a reusable persona library with create, edit, duplicate, delete, import, and export workflows
- Select one optional default persona for new conversations
- Freeze persona configuration into each conversation so library edits do not rewrite old chats
- Reassign or clear the persona used for future responses in an existing conversation
- Preview canonical message roles without sending a model request
- Preserve the real user message separately and unchanged
- Create, rename, open, search, import, export, and delete persistent conversations
- Render safe Markdown, GFM structures, tables, and highlighted code blocks
- Stream responses from the selected model through `POST /chat/completions`
- Persist completed messages and sanitized streaming failures
- Generate the first conversation title locally without spending a model request
- Edit a user message and replace the conversation tail with a new response
- Regenerate any finished assistant response using the preceding user message
- Stop an active response without treating it as an upstream failure
- Save partial output during long streams and recover abandoned streams after restart
- Reject concurrent generations within the same conversation

Utility falls back to primary when it is not configured. Image generation remains disabled until an image model is explicitly selected.

## Explicitly out of scope

- Multiple users, invitations, roles, or per-user data isolation
- Email password recovery
- Agents and tool execution
- Memory and retrieval-augmented generation
- MCP integrations
- Schedulers and automations
- Email and calendar integrations
- Automatic persona synchronization or full persona revision history
- Dynamic cost-aware, latency-aware, or conversation-scoped model routing
- Image-generation user interface
- Application-wide mobile shell remediation

## Architecture

```text
apps/web  Next.js user interface
apps/api  FastAPI application and database migrations
postgres  Optional bundled PostgreSQL database
```

Docker Compose is the initial deployment target. Redis is intentionally absent because the current application does not require a queue or distributed state.

## Requirements

- Docker with Compose support

For local development outside containers:

- Node.js 22+
- pnpm 10+
- Python 3.13+
- uv
- PostgreSQL 17+

## Start with the bundled PostgreSQL database

Create the local environment file:

```bash
cp .env.example .env
```

Generate an encryption key:

```bash
openssl rand -hex 32
```

Set the generated value as `ASTER_ENCRYPTION_KEY` in `.env`. Keep this value stable after storing endpoint credentials.

The example environment enables the `local-db` Compose profile:

```env
COMPOSE_PROFILES=local-db
POSTGRES_DB=aster
POSTGRES_USER=aster
POSTGRES_PASSWORD=aster
DATABASE_URL=
```

When `DATABASE_URL` is empty, the API builds the local connection URL from the bundled PostgreSQL settings. Existing installations can keep their current database name, user, and password without copying credentials into a second setting.

The bundled database always uses port 5432 inside the Compose network and does not publish a database port to the host. An old `POSTGRES_PORT` entry may remain in an existing `.env`; it is no longer used by the Compose deployment.

Start Aster:

```bash
docker compose up -d --build
```

The bundled database is stored in the `postgres-data` Docker volume.

## First sign-up

Open Aster after the containers become healthy:

- Local: http://localhost:3000
- LAN example: http://192.168.1.20:3000

When no owner exists, Aster redirects to `/setup`. Create the username and password there. That transaction creates the only owner and permanently closes public sign-up.

No owner username or password belongs in `.env`.

After setup:

- unauthenticated visitors are redirected to `/login`;
- chat, model, persona, and account APIs require a valid session;
- passwords are stored as Argon2id hashes;
- browser sessions use an `HttpOnly` cookie;
- only a SHA-256 digest of the random session token is stored in PostgreSQL.

## Use an external PostgreSQL database

Edit `.env`, disable the bundled database profile, and provide the external URL:

```env
COMPOSE_PROFILES=
DATABASE_URL=postgresql+asyncpg://user:password@database-host:5432/aster
```

An explicit `DATABASE_URL` takes precedence over every local PostgreSQL setting. The database host must be reachable from the API container.

Start the same stack:

```bash
docker compose up -d --build
```

Only the API and web services start when `COMPOSE_PROFILES` is empty.

The API runs Alembic migrations before starting, regardless of whether PostgreSQL is bundled or external.

## Open Aster

Default local addresses:

- Chat: http://localhost:3000
- Model settings: http://localhost:3000/settings/models
- Persona settings: http://localhost:3000/settings/persona
- Account settings: http://localhost:3000/settings/account
- API health: http://localhost:8000/health
- API readiness: http://localhost:8000/ready
- API documentation in development: http://localhost:8000/docs

API documentation is disabled when `APP_ENVIRONMENT=production`.

## Configure access from another machine

When the browser does not run on the Docker host, set the browser origin in `.env`:

```env
ASTER_CORS_ORIGINS=http://192.168.1.20:3000
ASTER_API_INTERNAL_URL=http://api:8000
ASTER_SESSION_SECURE=false
```

Browser API requests use the same web origin and are proxied internally to `ASTER_API_INTERNAL_URL`. The browser never needs the API port or a separate public API URL.

`ASTER_API_INTERNAL_URL` is used by server-side web requests inside the Compose network and normally remains `http://api:8000`.

## Expose Aster through HTTPS

Do not expose the raw development ports directly to the internet. Put Aster behind a trusted reverse proxy or tunnel and publish only the web service.

Recommended public layout:

```text
https://aster.example.com/ -> web:3000
```

Next.js proxies `/api` to FastAPI through the internal Compose network. The public reverse proxy must not bypass that path by routing `/api` directly to port 8000. Health and readiness checks may remain private.

Production environment:

```env
APP_ENVIRONMENT=production
ASTER_CORS_ORIGINS=https://aster.example.com
ASTER_API_INTERNAL_URL=http://api:8000
ASTER_SESSION_SECURE=true
```

The public hostname must terminate HTTPS. `ASTER_SESSION_SECURE=true` prevents the browser from sending the session cookie over plain HTTP.

After changing the public origin or secure-cookie setting:

```bash
docker compose up -d --force-recreate api web
```

The session cookie is host-only and belongs to the public web hostname.

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

- `ASTER_SESSION_ABSOLUTE_DAYS` limits the total session lifetime.
- `ASTER_SESSION_IDLE_HOURS` expires sessions that have not been used.
- `ASTER_SESSION_TOUCH_SECONDS` limits how often active-session timestamps are written.
- `ASTER_LOGIN_ATTEMPTS` and `ASTER_LOGIN_WINDOW_SECONDS` control the per-process login limiter.
- Password changes revoke every existing session and create a fresh session for the current browser.
- Account settings can revoke every other active session.

## Reset a forgotten password

Aster does not use email recovery or recovery questions. Server administrators reset the owner password inside the API container:

```bash
docker compose exec api python -m app.cli reset-password
```

The command prompts for the new password without printing it, updates the Argon2id hash, and revokes every active session.

## Runtime model timeouts

Model listing and initial endpoint connections use 30 seconds by default. Streaming reads use 120 seconds by default.

```env
ASTER_ENDPOINT_TIMEOUT_SECONDS=30
ASTER_STREAM_TIMEOUT_SECONDS=120
```

Increase these values for a slow endpoint without rebuilding the API image. Recreate the API container after changing them:

```bash
docker compose up -d --force-recreate api
```

## OpenAI-compatible endpoint format

Enter the API root as the base URL. Include `/v1` when the service exposes its OpenAI-compatible routes there.

```text
https://example.com/v1
```

Aster uses:

```text
GET  {base_url}/models
POST {base_url}/chat/completions
Authorization: Bearer <api-key>
```

Chat requests use the configured primary model and set `stream: true`. Optional model profiles add only explicitly configured generation fields. The API key is optional for local services that do not require authentication.

## Persona library and conversation snapshots

Persona settings support reusable identities with independent names, descriptions, instructions, enabled states, and instruction roles.

One enabled persona may be selected as the default. New conversations copy that persona into a frozen snapshot. Selecting no default creates new conversations without persona instructions.

Editing or deleting the source persona does not alter existing conversation snapshots. Reassigning a conversation replaces only the snapshot used for later model requests; existing messages remain unchanged.

Persona exports use the versioned `aster-persona` JSON format. Conversation export version 2 includes the optional persona snapshot, while version 1 conversation imports remain supported.

## Backup and upgrade

Back up the bundled database:

```bash
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > aster-backup.sql
```

External database deployments should use the backup process provided by their PostgreSQL host.

### Upgrade an existing bundled-database installation

Installations created before the `local-db` profile was added must add these lines to `.env` before the first upgrade:

```env
COMPOSE_PROFILES=local-db
DATABASE_URL=
```

Keep the existing `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` values unchanged. Do not remove the `postgres-data` volume. An existing `POSTGRES_PORT` line can remain, but it is ignored because PostgreSQL is no longer published to the host.

Upgrade the source checkout:

```bash
git pull --ff-only
docker compose up -d --build
```

The API applies pending migrations automatically.

The Stage 11 migration moves the original global persona into the persona library, preserves its instructions, selects it as the default when it was enabled, and snapshots it into existing conversations. Conversations, messages, endpoints, model caches, and encrypted credentials are otherwise preserved.

Changing `ASTER_ENCRYPTION_KEY` without re-encrypting stored endpoint credentials makes those credentials unreadable.

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

## Security baseline

- Passwords are hashed with Argon2id and are never encrypted or stored in plain text.
- Session tokens are random, stored only as hashes, and delivered through `HttpOnly` cookies.
- Unsafe browser requests validate their origin.
- API responses are marked `Cache-Control: no-store`.
- Secrets must be supplied through environment variables or the application credential store.
- API keys are encrypted before being stored and are never returned by endpoint APIs.
- API keys, passwords, and session tokens must never be included in logs, error payloads, fixtures, or documentation.
- Upstream response bodies are not forwarded to the user.
- The bundled PostgreSQL service is not published to the host.
- Model-provider behavior is implemented through generic API contracts rather than hard-coded provider names.

## Status

Stages 1 through 11 have passed automated validation. Real deployment validation remains the release gate for each new stage before merge.
