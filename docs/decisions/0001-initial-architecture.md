# ADR-0001: Initial application architecture

- Status: Accepted
- Date: 2026-07-16

## Context

Aster needs a small but durable foundation for a self-hosted chat application. The architecture must support a browser user interface, persistent configuration and conversations, streamed model responses, and OpenAI-compatible endpoints without coupling the product to one provider.

The initial codebase is empty. This is the best point to establish clear boundaries without implementing future platform features prematurely.

## Decision

### Repository structure

Use one repository with two applications:

```text
apps/web  Next.js and TypeScript
apps/api  FastAPI and Python
```

Shared deployment and product documentation remain at the repository root.

### Web application

Use Next.js with the App Router and TypeScript. pnpm is the only JavaScript package manager used by the project.

### API application

Use FastAPI with SQLAlchemy's asynchronous API and asyncpg. Python dependencies and commands are managed with uv.

### Persistence

Use PostgreSQL from the beginning. Database changes are managed through Alembic migrations.

### Deployment

Docker Compose is the primary initial deployment method and starts three services:

- web
- api
- postgres

Redis is not included. The MVP has no queue, distributed scheduler, or cross-process ephemeral state requiring it.

### Communication

The browser application communicates with the API over HTTP. Streamed chat responses will use Server-Sent Events unless implementation evidence later demonstrates that WebSockets are required.

### Provider integration

The API will introduce a canonical internal request model and OpenAI-compatible adapters in a later implementation step. Provider-specific names and private infrastructure are not part of the application contract.

### Authentication

MVP 1 operates as a single-user application and does not implement accounts or sessions. Access control is expected at the deployment boundary when needed.

## Consequences

### Positive

- The user interface and model runtime can evolve independently.
- PostgreSQL provides a durable base for conversations, endpoint configuration, and model cache data.
- The initial deployment remains understandable and reproducible.
- The product avoids queue infrastructure before background jobs exist.
- Provider-neutral boundaries are established before endpoint integration is implemented.

### Negative

- Two language ecosystems require separate dependency and quality tooling.
- Deployment-level access control is required for installations exposed beyond a trusted network.
- A future multi-user release will require an explicit authentication and data-isolation milestone.

## Deferred decisions

The following are deliberately unresolved:

- Authentication technology
- Background queue and scheduler
- Embedding and vector storage
- Tool execution and permissions
- MCP integration
- Model-specific advanced parameters
- Observability beyond foundational health checks and safe logs
