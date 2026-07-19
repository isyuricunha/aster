# Environment reference

[`.env.example`](../../.env.example) is the canonical deployment template. It groups settings by responsibility and includes the defaults used by the application and Docker Compose.

## Required settings

Only one variable is required for every deployment:

| Variable | Requirement | Purpose |
| --- | --- | --- |
| `ASTER_ENCRYPTION_KEY` | At least 32 characters | Encrypts endpoint, MCP, communication, and integration credentials before storage. |

Generate a key with:

```bash
openssl rand -hex 32
```

Keep the value stable and back it up securely. Changing it after credentials have been stored makes those encrypted values unreadable.

## Database mode

Choose one database mode.

### Bundled PostgreSQL

The example file enables the bundled PostgreSQL service:

```env
COMPOSE_PROFILES=local-db
POSTGRES_DB=aster
POSTGRES_USER=aster
POSTGRES_PASSWORD=replace-with-a-strong-database-password
DATABASE_URL=
```

`POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` are required for this mode. The API constructs its internal async PostgreSQL URL from those values.

### External PostgreSQL

Disable the bundled profile and provide an async SQLAlchemy URL:

```env
COMPOSE_PROFILES=
DATABASE_URL=postgresql+asyncpg://user:password@database-host:5432/aster
```

`DATABASE_URL` is required for this mode. The bundled PostgreSQL variables are ignored by the API when a non-empty URL is present.

## Optional settings

Every setting below is optional. Removing one from `.env` uses the default shown here.

### Application and networking

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENVIRONMENT` | `development` | Use `production` for public deployments and production behavior. |
| `API_PORT` | `8000` | Host port published for FastAPI. Do not expose it publicly when the web proxy is available. |
| `WEB_PORT` | `3000` | Host port published for Next.js. |
| `ASTER_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated browser origins allowed to call the API. |
| `ASTER_API_INTERNAL_URL` | `http://api:8000` | Internal API origin used by the web container. |

### Model requests

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_ENDPOINT_TIMEOUT_SECONDS` | `30` | Timeout for non-streaming model and endpoint requests. |
| `ASTER_STREAM_TIMEOUT_SECONDS` | `120` | Timeout for streamed chat responses. |

### Sessions and login protection

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_SESSION_COOKIE_NAME` | `aster_session` | Owner session cookie name. |
| `ASTER_SESSION_SECURE` | `false` | Sends the session cookie only over HTTPS when true. |
| `ASTER_SESSION_ABSOLUTE_DAYS` | `30` | Absolute session lifetime. |
| `ASTER_SESSION_IDLE_HOURS` | `168` | Idle session lifetime. |
| `ASTER_SESSION_TOUCH_SECONDS` | `300` | Minimum interval between session activity updates. |
| `ASTER_LOGIN_ATTEMPTS` | `5` | Login attempts allowed inside the rate-limit window. |
| `ASTER_LOGIN_WINDOW_SECONDS` | `300` | Login rate-limit window. |

Set `ASTER_SESSION_SECURE=true` when Aster is served exclusively through HTTPS.

### MCP and interactive tools

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_MCP_STDIO_ENABLED` | `false` | Allows configured MCP stdio processes inside the API container. |
| `ASTER_MCP_TIMEOUT_SECONDS` | `30` | MCP connection and execution timeout. |
| `ASTER_TOOL_MAX_ROUNDS` | `8` | Maximum model/tool rounds in one interactive turn. |
| `ASTER_TOOL_ARGUMENT_MAX_CHARACTERS` | `100000` | Maximum serialized tool arguments. |
| `ASTER_TOOL_RESULT_MAX_CHARACTERS` | `100000` | Maximum stored tool result. |

### Memory, documents, and retrieval

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
| `ASTER_DOCUMENT_CHUNK_OVERLAP` | `200` | Character overlap between chunks. Must remain smaller than the chunk size. |
| `ASTER_DOCUMENT_MAX_CHUNKS` | `2000` | Maximum chunks per document. |
| `ASTER_EMBEDDING_BATCH_SIZE` | `64` | Maximum inputs sent in one embedding request. |

### Private media and images

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_MEDIA_ROOT` | `/var/lib/aster/media` | Shared private-media path mounted by API and worker. |
| `ASTER_IMAGE_TIMEOUT_SECONDS` | `300` | Provider image-operation timeout. |
| `ASTER_IMAGE_UPLOAD_MAX_BYTES` | `20000000` | Maximum image input size. |
| `ASTER_IMAGE_OUTPUT_MAX_BYTES` | `25000000` | Maximum provider image output size. |
| `ASTER_IMAGE_MAX_PIXELS` | `40000000` | Maximum decoded image pixel count. |
| `ASTER_IMAGE_MAX_INPUTS` | `8` | Maximum images in one edit operation. |
| `ASTER_IMAGE_MAX_OUTPUTS` | `4` | Maximum outputs in one generation operation. |

### Automations and integrations

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_AUTOMATION_POLL_SECONDS` | `2` | Worker polling interval for due automation work. |
| `ASTER_AUTOMATION_LEASE_SECONDS` | `120` | Automation run lease duration. |
| `ASTER_AUTOMATION_HEARTBEAT_SECONDS` | `30` | Automation lease renewal interval. |
| `ASTER_AUTOMATION_SCHEDULER_BATCH_SIZE` | `25` | Maximum definitions scheduled per cycle. |
| `ASTER_AUTOMATION_OUTPUT_MAX_CHARACTERS` | `100000` | Maximum stored automation model output. |
| `ASTER_INTEGRATION_TIMEOUT_SECONDS` | `30` | SMTP, CalDAV, webhook, IMAP, and Discord request timeout. |
| `ASTER_WEBHOOK_MAX_BYTES` | `1000000` | Maximum inbound webhook body size. |

`ASTER_AUTOMATION_HEARTBEAT_SECONDS` must remain less than half of `ASTER_AUTOMATION_LEASE_SECONDS`.

### Communications

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTER_COMMUNICATION_LEASE_SECONDS` | `180` | Communication synchronization lease duration. |
| `ASTER_COMMUNICATION_MESSAGE_MAX_CHARACTERS` | `200000` | Maximum persisted message content. |
| `ASTER_COMMUNICATION_ATTACHMENT_MAX_BYTES` | `15000000` | Maximum individual attachment size. |
| `ASTER_COMMUNICATION_MAX_ATTACHMENTS` | `16` | Maximum attachments per inbound message. |

### Autonomous agents

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

`ASTER_AGENT_HEARTBEAT_SECONDS` must remain less than half of `ASTER_AGENT_LEASE_SECONDS`.

## Applying changes

Validate the Compose configuration after editing `.env`:

```bash
docker compose config --quiet
```

Recreate services after changing application runtime values:

```bash
docker compose up -d --force-recreate api worker web
```

Changes to database mode, published ports, mounts, or images may require a normal rebuild:

```bash
docker compose up -d --build
```
