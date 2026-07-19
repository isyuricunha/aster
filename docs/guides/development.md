# Development

## Requirements

- Node.js 22+
- pnpm 10+
- Python 3.13+
- uv
- PostgreSQL 17+ or the bundled Compose database
- Docker with Compose support for full-stack validation

## Repository layout

```text
apps/api/                 FastAPI application, worker, tests, and Alembic migrations
apps/web/                 Next.js application
docs/                     guides, reference, product records, ADRs, and archive
scripts/ci/               executable full-stack contract checks
.github/workflows/ci.yml  active GitHub Actions validation
compose.yaml              deployment and integration-test stack
```

## Web

From the repository root:

```bash
pnpm install
pnpm lint
pnpm typecheck
pnpm build
```

Use pnpm for JavaScript dependencies and scripts.

## API

```bash
export ASTER_ENCRYPTION_KEY="development-key-with-at-least-32-characters"
cd apps/api
uv sync --frozen --group dev
uv run ruff check .
uv run pytest
uv run alembic upgrade head
```

## Full stack

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Readiness:

```bash
curl -fsS http://localhost:${API_PORT:-8000}/ready
docker compose exec -T worker test -f /tmp/aster-worker-ready
```

## CI

The active workflow is `.github/workflows/ci.yml`.

It validates:

- ESLint;
- TypeScript;
- the production Next.js build;
- Ruff;
- the complete API test suite;
- Alembic migration rendering;
- bundled and external database Compose configuration;
- Docker image builds;
- stack startup and readiness;
- core, memory, images, automations, communications, agents, and tools contracts;
- clean stack shutdown.

The scripts under `scripts/ci/` are executable product contracts. Stage-oriented filenames are retained because they describe the historical contract boundary, not because development still requires stage branches.

## Change workflow

Work directly on `main` only for small, reviewable changes with immediate CI validation.

Use a temporary branch for changes that are destructive, difficult to roll back, schema-heavy, security-sensitive, or likely to require parallel review.

In either case:

1. keep commits focused;
2. update tests and documentation together;
3. do not continue stacking unrelated changes on a failing commit;
4. never commit credentials, private endpoints, user data, media, or backups;
5. preserve provider-neutral naming in code and public documentation.

## Documentation

Update the canonical guide or reference when behavior changes.

- procedures belong in `docs/guides/`;
- stable implementation contracts belong in `docs/reference/`;
- product principles belong in `docs/product/`;
- durable architectural choices belong in `docs/decisions/`;
- completed rollout notes belong in `docs/archive/`.

Keep the root README concise.
