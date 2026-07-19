# Architecture reference

## Deployment model

Aster is a single-owner self-hosted application deployed as a Docker Compose stack.

```text
web       Next.js UI and same-origin API proxy
api       FastAPI application and authenticated API
worker    automation, communication, and agent background runtime
postgres  optional bundled PostgreSQL 17 service
```

The API and worker are built from `apps/api`. The web image is built from the repository root with `apps/web/Dockerfile`.

## Request flow

The browser uses the web origin. Next.js proxies `/api` requests to the internal FastAPI service through `ASTER_API_INTERNAL_URL`.

This keeps browser sessions, origin validation, application pages, and authenticated API requests on one public origin.

FastAPI documentation is available in development and disabled when `APP_ENVIRONMENT=production`.

## Persistence

### PostgreSQL

PostgreSQL stores:

- owner authentication and opaque session hashes;
- encrypted model, MCP, communication, and integration credentials;
- endpoint catalogs and model profiles;
- personas and frozen snapshots;
- conversations, messages, tool executions, and retrieval provenance;
- approved memories, suggestions, collections, documents, chunks, and vectors;
- image-operation metadata and media relationships;
- automations, schedules, runs, deliveries, notifications, and webhook deduplication;
- communication accounts, cursors, threads, messages, rules, and deliveries;
- agents, immutable run scopes, steps, approvals, budgets, notifications, and event rules.

PostgreSQL is also the durable queue for automations and agents. A separate queue service is not required.

### Private media

The `aster-media` volume stores media bytes outside PostgreSQL:

- image inputs and outputs;
- communication attachments.

The API and worker mount the same path. Media is served only through authenticated routes.

## Background worker

The worker:

- schedules and claims automation runs;
- renews automation leases;
- synchronizes communication accounts;
- dispatches communication rules;
- schedules and claims agent runs;
- processes approvals and bounded retries;
- creates notifications and records external delivery attempts.

Claims use durable database state and expiring leases. A worker that loses ownership stops local execution. Uncertain external side effects are not silently replayed.

## Model integration

OpenAI-compatible APIs are the preferred contracts for:

- model catalog discovery;
- streamed chat completions;
- embeddings;
- image generation;
- image editing.

Provider behavior is controlled through explicit endpoint settings, model profiles, image profiles, and role selection rather than provider-name checks.

## MCP integration

Interactive and agent tools use MCP.

Streamable HTTP is enabled by default. stdio is opt-in because it executes local processes inside the API container.

Aster owns discovery, enablement, scope, confirmation, execution, persistence, limits, and errors. Models never receive MCP credentials.

## Retrieval

Lexical retrieval is always available. Optional embeddings add semantic scoring.

Vectors are stored as JSON arrays in PostgreSQL. A separate vector database and pgvector are not required.

Memory and document content enter model context as untrusted developer data. Selected sources are persisted against the assistant response.

## Security boundaries

- The browser authenticates through an opaque `HttpOnly` session cookie.
- Unsafe authenticated browser requests validate their origin.
- Passwords use Argon2id.
- Stored credentials are encrypted with `ASTER_ENCRYPTION_KEY`.
- Webhook tokens and session tokens are stored as hashes.
- Remote content, tool results, communications, memory, documents, and trigger payloads remain untrusted.
- The bundled PostgreSQL service is not published to the host.
- Public deployments should expose the web service, not the private API as a separate application origin.

See [Security reference](security.md).
