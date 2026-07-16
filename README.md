# Aster

Aster is a self-hosted AI chat application designed around user-defined personas and OpenAI-compatible model endpoints.

The first MVP is feature-complete: endpoint and model configuration, one global persona, persistent conversations, streamed responses, message replacement, regeneration, explicit stop controls, and interrupted-stream recovery.

## MVP scope

- Persistent chat with streamed responses
- One global, user-defined persona
- OpenAI-compatible endpoint and model configuration
- Primary, utility, and image model roles
- Model listing and local cache

Utility falls back to primary when it is not configured. Image generation remains disabled until an image model is explicitly selected.

## Current capabilities

- Register, edit, disable, test, and delete OpenAI-compatible endpoints
- Encrypt optional Bearer API keys before storing them in PostgreSQL
- Synchronize model IDs from `GET /models`
- Preserve cached model entries when an endpoint is unavailable
- Mark discovered models missing from a later sync without deleting them
- Add model IDs manually
- Select primary, utility, and image model roles
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
postgres  Persistent application database
```

Docker Compose is the initial deployment target. Redis is intentionally absent because the current milestone does not require a queue or distributed state.

## Requirements

- Docker with Compose support

For local development outside containers:

- Node.js 22+
- pnpm 10+
- Python 3.13+
- uv
- PostgreSQL 17+

## Start with Docker Compose

```bash
cp .env.example .env
```

Replace the example encryption key before storing credentials:

```bash
openssl rand -hex 32
```

Set the generated value as `ASTER_ENCRYPTION_KEY` in `.env`, then start Aster:

```bash
docker compose up --build
```

Open:

- Chat: http://localhost:3000
- Model settings: http://localhost:3000/settings/models
- Persona settings: http://localhost:3000/settings/persona
- API health: http://localhost:8000/health
- API readiness: http://localhost:8000/ready
- API documentation: http://localhost:8000/docs

The database is stored in the `postgres-data` Docker volume and survives container restarts.

`ASTER_ENCRYPTION_KEY` must remain stable after endpoints are created. Changing it without re-encrypting existing credentials makes those credentials unreadable.

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

- [Project charter](docs/product/project-charter.md)
- [ADR-0001: Initial architecture](docs/decisions/0001-initial-architecture.md)
- [ADR-0002: Model endpoints and local model cache](docs/decisions/0002-model-endpoints-and-cache.md)
- [ADR-0003: Global persona and canonical message composition](docs/decisions/0003-persona-and-message-composition.md)
- [ADR-0004: Persistent chat and streamed completions](docs/decisions/0004-persistent-chat-and-streaming.md)
- [ADR-0005: Linear chat replacement and generation lifecycle](docs/decisions/0005-chat-generation-lifecycle.md)

## Security baseline

- Secrets must be supplied through environment variables or the application credential store.
- API keys are encrypted before being stored and are never returned by endpoint APIs.
- API keys must never be included in logs, error payloads, fixtures, or documentation.
- Upstream response bodies are not forwarded to the user.
- Model-provider behavior is implemented through generic API contracts rather than hard-coded provider names.

## Status

MVP 1 is feature-complete and ready for real-endpoint release validation. The application keeps a linear conversation history: editing or regenerating an earlier message intentionally replaces every later message.
