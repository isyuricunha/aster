# Environment reference

`.env.example` is the canonical machine-readable list. This document explains each setting by area.

## Core deployment

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENVIRONMENT` | `development` | Enables development behavior. Use `production` for public deployments. |
| `COMPOSE_PROFILES` | `local-db` | Enables the bundled PostgreSQL service. Set empty for an external database. |
| `POSTGRES_DB` | `aster` | Bundled database name. |
| `POSTGRES_USER` | `aster` | Bundled database user. |
| `POSTGRES_PASSWORD` | `aster` | Bundled database password. Replace outside disposable local use. |
| `DATABASE_URL` | empty | Async SQLAlchemy PostgreSQL URL for an external database. |
| `API_PORT` | `8000` | Host port published for FastAPI. |
| `WEB_PORT` | `3000` | Host port published for Next.js. |
| `ASTER_API_INTERNAL_URL` | `http://api:8000` | Internal API origin used by the web service. |
| `ASTER_CORS_ORIGINS` | `http://localhost:3000` | Allowed browser origins. |
| `ASTER_ENCRYPTION_KEY` | required | Encrypts stored credentials. Use at least 32 characters and preserve it. |

## Sessions and login

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_SESSION_COOKIE_NAME` | `aster_session` | Owner session cookie name. |
| `ASTER_SESSION_SECURE` | `false` | Sends the session cookie only over HTTPS when true. |
| `ASTER_SESSION_ABSOLUTE_DAYS` | `30` | Absolute session lifetime. |
| `ASTER_SESSION_IDLE_HOURS` | `168` | Idle session lifetime. |
| `ASTER_SESSION_TOUCH_SECONDS` | `300` | Minimum interval between session activity updates. |
| `ASTER_LOGIN_ATTEMPTS` | `5` | Login attempts allowed inside the rate-limit window. |
| `ASTER_LOGIN_WINDOW_SECONDS` | `300` | Login rate-limit window. |

## Model requests

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_ENDPOINT_TIMEOUT_SECONDS` | `30` | Non-streaming model and endpoint request timeout. |
| `ASTER_STREAM_TIMEOUT_SECONDS` | `120` | Streaming chat timeout. |

## MCP and tools

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_MCP_STDIO_ENABLED` | `false` | Allows configured MCP stdio processes inside the API container. |
| `ASTER_MCP_TIMEOUT_SECONDS` | `30` | MCP connection and execution timeout. |
| `ASTER_TOOL_MAX_ROUNDS` | `8` | Maximum tool/model rounds in one interactive turn. |
| `ASTER_TOOL_ARGUMENT_MAX_CHARACTERS` | `100000` | Maximum serialized tool arguments. |
| `ASTER_TOOL_RESULT_MAX_CHARACTERS` | `100000` | Maximum stored tool result. |

## Memory, documents, and retrieval

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_MEMORY_MAX_ITEMS` | `12` | Maximum approved memories selected for one request. |
| `ASTER_MEMORY_SUGGESTION_MAX_ITEMS` | `8` | Maximum suggestions generated in one extraction. |
| `ASTER_RAG_MAX_SOURCES` | `8` | Maximum document sources selected for one request. |
| `ASTER_RAG_CONTEXT_MAX_CHARACTERS` | `24000` | Maximum retrieval context inserted into a request. |
| `ASTER_RAG_CANDIDATE_LIMIT` | `2000` | Candidate ceiling before ranking. |
| `ASTER_DOCUMENT_MAX_BYTES` | `5000000` | Maximum uploaded document size. |
| `ASTER_DOCUMENT_MAX_CHARACTERS` | `2000000` | Maximum extracted text size. |
| `ASTER_DOCUMENT_CHUNK_CHARACTERS` | `1600` | Deterministic chunk target size. |
| `ASTER_DOCUMENT_CHUNK_OVERLAP` | `200` | Character overlap between chunks. |
| `ASTER_DOCUMENT_MAX_CHUNKS` | `2000` | Maximum chunks per document. |
| `ASTER_EMBEDDING_BATCH_SIZE` | `64` | Maximum embedding batch size. |

## Media and images

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_MEDIA_ROOT` | `/var/lib/aster/media` | Shared private-media path mounted by API and worker. |
| `ASTER_IMAGE_TIMEOUT_SECONDS` | `300` | Provider image-operation timeout. |
| `ASTER_IMAGE_UPLOAD_MAX_BYTES` | `20000000` | Maximum image input size. |
| `ASTER_IMAGE_OUTPUT_MAX_BYTES` | `25000000` | Maximum provider image output size. |
| `ASTER_IMAGE_MAX_PIXELS` | `40000000` | Maximum decoded image pixel count. |
| `ASTER_IMAGE_MAX_INPUTS` | `8` | Maximum images in one edit operation. |
| `ASTER_IMAGE_MAX_OUTPUTS` | `4` | Maximum outputs in one generation operation. |

## Automations and integrations

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_AUTOMATION_POLL_SECONDS` | `2` | Worker automation polling interval. |
| `ASTER_AUTOMATION_LEASE_SECONDS` | `120` | Automation run lease duration. |
| `ASTER_AUTOMATION_HEARTBEAT_SECONDS` | `30` | Automation lease renewal interval. Must remain below half the lease duration. |
| `ASTER_AUTOMATION_SCHEDULER_BATCH_SIZE` | `25` | Maximum definitions scheduled per cycle. |
| `ASTER_AUTOMATION_OUTPUT_MAX_CHARACTERS` | `100000` | Maximum stored automation model output. |
| `ASTER_INTEGRATION_TIMEOUT_SECONDS` | `30` | SMTP, CalDAV, webhook, IMAP, and Discord request timeout. |
| `ASTER_WEBHOOK_MAX_BYTES` | `1000000` | Maximum inbound webhook body size. |

## Communications

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_COMMUNICATION_LEASE_SECONDS` | `180` | Communication synchronization lease duration. |
| `ASTER_COMMUNICATION_MESSAGE_MAX_CHARACTERS` | `200000` | Maximum persisted message content. |
| `ASTER_COMMUNICATION_ATTACHMENT_MAX_BYTES` | `15000000` | Maximum individual attachment size. |
| `ASTER_COMMUNICATION_MAX_ATTACHMENTS` | `16` | Maximum attachments per inbound message. |

## Agents

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_AGENT_LEASE_SECONDS` | `180` | Agent run lease duration. |
| `ASTER_AGENT_HEARTBEAT_SECONDS` | `45` | Agent lease renewal interval. |
| `ASTER_AGENT_SCHEDULER_BATCH_SIZE` | `25` | Maximum agents scheduled per cycle. |
| `ASTER_AGENT_DISPATCH_BATCH_SIZE` | `100` | Maximum communication events dispatched per cycle. |
| `ASTER_AGENT_OUTPUT_MAX_CHARACTERS` | `100000` | Maximum final agent output. |
| `ASTER_AGENT_HISTORY_MAX_CHARACTERS` | `50000` | Maximum serialized run history supplied to the model. |
| `ASTER_AGENT_RETRIEVAL_MAX_CHARACTERS` | `24000` | Maximum retrieval context for an agent run. |
| `ASTER_AGENT_LOOP_REPEAT_LIMIT` | `3` | Repeated-decision threshold used by loop protection. |

## Applying changes

Validate the Compose configuration:

```bash
docker compose config --quiet
```

Recreate services after changing runtime values:

```bash
docker compose up -d --force-recreate api worker web
```

Changes to database profile, ports, mounts, or images may require a normal rebuild:

```bash
docker compose up -d --build
```
