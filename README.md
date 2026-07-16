# Aster

Aster is a self-hosted AI chat application designed around user-defined personas and OpenAI-compatible model endpoints.

The repository is currently in its foundation stage. The first stable MVP is intentionally small and focuses on a reliable chat experience rather than a broad agent platform.

## MVP scope

- Persistent chat with streamed responses
- One global, user-defined persona
- OpenAI-compatible endpoint and model configuration
- Primary, utility, and image model slots
- Model listing and local cache

The utility model falls back to the primary model when it is not configured. The image model may fall back to the primary model only when the configured endpoint exposes compatible image-generation capabilities.

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

The initial deployment target is Docker Compose. Redis is intentionally not part of the foundation because the MVP does not yet require a queue or distributed state.

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
docker compose up --build
```

Then open:

- Web: http://localhost:3000
- API health: http://localhost:8000/health
- API readiness: http://localhost:8000/ready
- API documentation: http://localhost:8000/docs

The database is stored in the `postgres-data` Docker volume and survives container restarts.

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
cd apps/api
uv sync --group dev
uv run ruff check .
uv run pytest
uv run alembic upgrade head
```

## Project documentation

- [Project charter](docs/product/project-charter.md)
- [ADR-0001: Initial architecture](docs/decisions/0001-initial-architecture.md)

## Security baseline

- Secrets must be supplied through environment variables or a future secret-storage layer.
- API keys must never be included in logs, error payloads, fixtures, or documentation.
- Model-provider behavior must be implemented through generic capabilities and API adapters rather than hard-coded provider names.

## Status

Foundation work only. Chat, persona management, endpoint management, and model caching will be implemented in subsequent milestones.
