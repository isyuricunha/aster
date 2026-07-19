<div align="center">

# Aster

**A private, self-hosted AI workspace for chat, memory, tools, media, communications, automations, and bounded agents.**

[![CI](https://github.com/isyuricunha/aster/actions/workflows/ci.yml/badge.svg)](https://github.com/isyuricunha/aster/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-7c83ff.svg)](LICENSE)
[![Docker Compose](https://img.shields.io/badge/deploy-Docker%20Compose-2496ed.svg)](compose.yaml)

</div>

Aster gives one owner a durable AI workspace without tying the product to a specific model provider. Connect OpenAI-compatible endpoints, choose explicit model roles, define personas, approve memory, retrieve private documents, use controlled MCP tools, manage communications, schedule automations, and run bounded agents from one interface.

The default deployment keeps application data in PostgreSQL and private media in a local Docker volume. Credentials are encrypted before storage, model access is explicit, and side effects remain visible and bounded.

## Highlights

- **Persistent chat** — streamed responses, reasoning disclosure, edit and resend, regeneration, stop, search, import, and export.
- **Provider-neutral models** — multiple OpenAI-compatible endpoints, cached catalogs, per-model profiles, explicit roles, and ordered fallbacks.
- **Personas and context** — reusable personas, frozen conversation snapshots, approved memory, private collections, lexical retrieval, and optional embeddings.
- **Controlled tools** — MCP over Streamable HTTP or opt-in stdio, per-tool enablement, conversation scopes, confirmations, and audit history.
- **Private media** — image generation and editing, validated uploads, private storage, gallery history, and chat attachments.
- **Durable workspaces** — automations, IMAP and Discord communications, manual and AI-assisted replies, and bounded persistent agents.
- **Desktop-first interface** — unified sidebar, command palette, floating workspaces, compact settings, and responsive mobile behavior.
- **Single-owner security model** — first-access setup, Argon2id passwords, opaque sessions, encrypted credentials, and no public sign-up after initialization.

## Quick start

### Requirements

- Docker with Compose support

### 1. Configure the deployment

```bash
cp .env.example .env
openssl rand -hex 32
```

Set the generated value as `ASTER_ENCRYPTION_KEY` in `.env`.

The example configuration enables the bundled PostgreSQL service through the `local-db` Compose profile.

### 2. Start Aster

```bash
docker compose up -d --build
docker compose ps
```

Open `http://localhost:3000`. On first access, Aster redirects to `/setup` so the single owner account can be created.

### 3. Connect a model

Open **Settings → Models** and:

1. add an OpenAI-compatible endpoint;
2. test the connection and synchronize its model catalog;
3. select a **Primary** model;
4. optionally select Utility, Image, and Embedding models.

Aster expects the endpoint root, including `/v1` when required by the provider.

## Architecture

```text
Browser
  │
  ▼
Next.js web ── same-origin /api proxy ──► FastAPI
                                              │
                       ┌──────────────────────┼──────────────────────┐
                       ▼                      ▼                      ▼
                 PostgreSQL            private media         model / MCP /
              state and queues          Docker volume        integration APIs
                       ▲
                       │
                    worker
       automations, communications, and agents
```

The default stack contains four services:

```text
postgres   optional bundled PostgreSQL 17
api        FastAPI, migrations, model adapters, retrieval, and integrations
worker     durable background scheduling and execution
web        Next.js application and same-origin API proxy
```

Redis, Celery, RabbitMQ, a separate vector database, and public object storage are not required by the default deployment.

## Documentation

Start with the [documentation index](docs/README.md).

| Area | Documentation |
| --- | --- |
| Install and deploy | [Installation](docs/guides/installation.md) |
| Configure Aster | [Configuration](docs/guides/configuration.md) |
| Use the workspaces | [Core workspaces](docs/guides/core-workspaces.md) |
| Communications | [Communication Hub](docs/guides/communication-hub.md) |
| Agents | [Autonomous agents](docs/guides/autonomous-agents.md) |
| Back up and upgrade | [Backup and upgrade](docs/guides/backup-and-upgrade.md) |
| Develop and validate | [Development](docs/guides/development.md) |
| Environment variables | [Environment reference](docs/reference/environment.md) |
| Architecture | [Architecture reference](docs/reference/architecture.md) |
| Security | [Security reference](docs/reference/security.md) |
| Product direction | [Project charter](docs/product/project-charter.md) · [Roadmap](docs/product/roadmap.md) |
| Decisions | [Architecture decision records](docs/decisions/README.md) |

## Development

Web checks:

```bash
pnpm install
pnpm lint
pnpm typecheck
pnpm build
```

API checks:

```bash
export ASTER_ENCRYPTION_KEY="development-key-with-at-least-32-characters"
cd apps/api
uv sync --frozen --group dev
uv run ruff check .
uv run pytest
uv run alembic upgrade head
```

The complete stack and application contracts are validated by `.github/workflows/ci.yml`.

## Project status

Aster is under active development. New work is selected from concrete self-hosted workflows and deployment feedback rather than speculative dashboards or automatic policy.

See the [changelog](CHANGELOG.md) for implemented changes and the [roadmap](docs/product/roadmap.md) for current direction.

## License

Aster is licensed under the [GNU Affero General Public License v3.0](LICENSE).
