# Aster

Aster is a self-hosted AI chat application built around user-defined personas and OpenAI-compatible model endpoints.

MVP 1 is feature-complete and has been validated against a real endpoint with a model cache containing more than one thousand entries.

## MVP scope

- Persistent chat with streamed responses
- One global, user-defined persona
- OpenAI-compatible endpoint and model configuration
- Primary, utility, and image model roles
- Persistent model discovery and local cache

Utility falls back to primary when it is not configured. Image generation remains disabled until an image model is explicitly selected.

## Current capabilities

- Register, edit, disable, test, and delete OpenAI-compatible endpoints
- Encrypt optional Bearer API keys before storing them in PostgreSQL
- Synchronize model IDs from `GET /models`
- Preserve cached model entries when an endpoint is unavailable
- Mark discovered models missing from a later sync without deleting them
- Add model IDs manually
- Search and browse large model caches without rendering the entire list at once
- Select primary, utility, and image model roles through searchable selectors
- Resolve utility to primary when utility is not configured
- Configure one global persona with a developer or system instruction role
- Preview canonical message roles without sending a model request
- Preserve the real user message separately and unchanged
- Create, rename, open, and delete persistent conversations
- Stream responses from the primary model through `POST /chat/completions`
- Persist completed messages and sanitized streaming failures
- Generate the first conversation title locally without spending a model request
- Edit a user message and replace the conversation tail with a new response
- Regenerate any finished assistant response using the preceding user message
- Stop an active response without treating it as an upstream failure
- Save partial output during long streams and recover abandoned streams after restart
- Reject concurrent generations within the same conversation

## Explicitly out of scope for MVP 1

- Agents and tool execution
- Memory and retrieval-augmented generation
- MCP integrations
- Schedulers and automations
- Email and calendar integrations
- Multiple or versioned personas
- Advanced per-model parameters
- Intelligent routing and fallback chains
- Image-generation user interface

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
- API health: http://localhost:8000/health
- API readiness: http://localhost:8000/ready
- API documentation: http://localhost:8000/docs

## Configure access from another machine

When the browser does not run on the Docker host, set public addresses in `.env`:

```env
ASTER_CORS_ORIGINS=http://192.168.1.20:3000
NEXT_PUBLIC_ASTER_API_URL=http://192.168.1.20:8000
ASTER_API_INTERNAL_URL=http://api:8000
```

`NEXT_PUBLIC_ASTER_API_URL` is compiled into the browser bundle. Rebuild the web image after changing it:

```bash
docker compose up -d --build web
```

`ASTER_API_INTERNAL_URL` is used by server-side web requests inside the Compose network and normally remains `http://api:8000`.

Use HTTPS before exposing Aster outside a trusted network. Configure `ASTER_CORS_ORIGINS` with the final browser origin.

## Runtime timeouts

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

Chat requests use the configured primary model and set `stream: true`. The API key is optional for local services that do not require authentication.

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

Changing `ASTER_ENCRYPTION_KEY` without re-encrypting stored credentials makes those credentials unreadable.

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

## Security baseline

- Secrets must be supplied through environment variables or the application credential store.
- API keys are encrypted before being stored and are never returned by endpoint APIs.
- API keys must never be included in logs, error payloads, fixtures, or documentation.
- Upstream response bodies are not forwarded to the user.
- The bundled PostgreSQL service is not published to the host.
- Model-provider behavior is implemented through generic API contracts rather than hard-coded provider names.

## Status

MVP 1 has passed real-endpoint validation and is being prepared for the `v0.1.0` release. Aster keeps one linear conversation history: editing or regenerating an earlier message intentionally replaces every later message.
