# Aster

Aster is a self-hosted AI workspace built around user-defined personas, OpenAI-compatible model endpoints, controlled MCP tools, approved personal memory, private document retrieval, and private image generation and editing.

## Current capabilities

- First-access creation of one owner account
- Argon2id password hashing and opaque server-side sessions
- Login rate limiting, password changes, logout, and session revocation
- OpenAI-compatible endpoint registration, testing, model discovery, and encrypted API credentials
- Searchable primary, utility, image, and embedding model selection
- Per-model chat profiles and explicit image capability profiles
- Ordered chat fallback routing that never combines partial model output
- Reusable personas with frozen conversation snapshots
- Persistent streamed conversations with edit, resend, regenerate, stop, search, import, and export
- Safe Markdown, GFM, highlighted code blocks, and copy controls
- MCP servers over Streamable HTTP and opt-in stdio
- Tool discovery, conversation scope, confirmation policies, execution history, and visible results
- Approved personal memory with global or persona scope
- Utility-model memory suggestions that require explicit acceptance
- Private knowledge collections and bounded document ingestion
- Lexical retrieval with optional OpenAI-compatible embeddings
- Per-conversation memory, RAG, and collection controls
- Visible and persisted retrieval provenance for assistant responses
- OpenAI-compatible image generation and editing from chat
- PNG, JPEG, and WebP visual inputs with optional masks
- Private image attachments, gallery, operation history, and conversation association
- Provider-aware image defaults and bounded additional parameters

## Architecture

```text
apps/web  Next.js user interface and same-origin API proxy
apps/api  FastAPI application, model adapters, MCP client, retrieval, private media, and migrations
postgres  Optional bundled PostgreSQL database
media     Private image files in the aster-media Docker volume
```

Docker Compose is the initial deployment target. Redis, a background queue, pgvector, ChromaDB, and public object storage are intentionally absent from the default stack.

## Requirements

- Docker with Compose support

For local development outside containers:

- Node.js 22+
- pnpm 10+
- Python 3.13+
- uv
- PostgreSQL 17+

## Start with the bundled PostgreSQL database

Create the environment file:

```bash
cp .env.example .env
```

Generate an encryption key:

```bash
openssl rand -hex 32
```

Set the generated value as `ASTER_ENCRYPTION_KEY` in `.env`. Keep it stable after storing endpoint or MCP credentials.

The example environment enables the bundled database:

```env
COMPOSE_PROFILES=local-db
POSTGRES_DB=aster
POSTGRES_USER=aster
POSTGRES_PASSWORD=aster
DATABASE_URL=
```

Start Aster:

```bash
docker compose up -d --build
```

The bundled database is stored in the `postgres-data` Docker volume. Private uploaded and generated images are stored separately in the `aster-media` volume. Neither service is published as public storage.

## First sign-up

Open the web application after the containers become healthy:

- Local: `http://localhost:3000`
- LAN example: `http://192.168.1.20:3000`

When no owner exists, Aster redirects to `/setup`. Create the username and password there. That transaction creates the only owner and closes public sign-up.

No owner username or password belongs in `.env`.

## Use an external PostgreSQL database

Disable the bundled database profile and provide an async PostgreSQL URL:

```env
COMPOSE_PROFILES=
DATABASE_URL=postgresql+asyncpg://user:password@database-host:5432/aster
```

Start the same stack:

```bash
docker compose up -d --build
```

Only the API and web services start when `COMPOSE_PROFILES` is empty. The API applies pending Alembic migrations before starting. The `aster-media` volume remains part of the application stack unless a different `ASTER_MEDIA_ROOT` is mounted deliberately.

## Open Aster

Default local routes:

- Chat: `http://localhost:3000`
- Images: `http://localhost:3000/images`
- Models: `http://localhost:3000/settings/models`
- Personas: `http://localhost:3000/settings/persona`
- Tools: `http://localhost:3000/settings/tools`
- Memory & Knowledge: `http://localhost:3000/settings/memory`
- Account: `http://localhost:3000/settings/account`
- API readiness: `http://localhost:8000/ready`
- API documentation in development: `http://localhost:8000/docs`

API documentation is disabled when `APP_ENVIRONMENT=production`.

## Remote access

When the browser runs on another machine, set the browser origin:

```env
ASTER_CORS_ORIGINS=http://192.168.1.20:3000
ASTER_API_INTERNAL_URL=http://api:8000
ASTER_SESSION_SECURE=false
```

The browser uses the web origin and Next.js proxies `/api` to FastAPI through the Compose network.

For public access, terminate HTTPS at a trusted reverse proxy or tunnel and publish only the web service:

```text
https://aster.example.com/ -> web:3000
```

Production settings:

```env
APP_ENVIRONMENT=production
ASTER_CORS_ORIGINS=https://aster.example.com
ASTER_API_INTERNAL_URL=http://api:8000
ASTER_SESSION_SECURE=true
```

Do not route public `/api` traffic directly to port 8000. The session cookie belongs to the web hostname.

## OpenAI-compatible endpoints

Enter the API root as the base URL. Include `/v1` when required:

```text
https://example.com/v1
```

Aster may use:

```text
GET  {base_url}/models
POST {base_url}/chat/completions
POST {base_url}/embeddings
POST {base_url}/images/generations
POST {base_url}/images/edits
Authorization: Bearer <api-key>
```

`/embeddings` is used only when an embedding model is selected. Chat and private document retrieval remain functional without it.

Image generation uses JSON requests. Image editing uses multipart form data with one or more images and an optional mask. Aster accepts either base64 image results or provider URLs, downloads URL results immediately, validates them, and stores the durable result privately.

## Model roles

- **Primary** — chat, reasoning, and model-requested tools
- **Utility** — bounded support work such as memory-candidate extraction; falls back to Primary
- **Image** — image generation and editing
- **Embedding** — optional semantic indexing and retrieval

The Image role may be left empty. In that case Aster uses the Primary model only when that exact cached model has an image profile declaring the required capability. Model names are never used to guess image support.

Chat profiles configure temperature, top-p, output limits, reasoning effort, token-field compatibility, and declared chat or streaming support.

Image profiles configure explicit generation, editing, multiple-input, and mask support; maximum inputs; output count; normalized defaults; and bounded provider parameters.

## Personas

Personas are reusable identities with independent names, descriptions, instructions, enabled states, and instruction roles.

One enabled persona may be selected as the default. New conversations copy it into a frozen snapshot. Editing or deleting the source persona does not rewrite existing conversations.

## Tools and MCP

Configure MCP servers under **Settings → Tools**.

Supported transports:

- Streamable HTTP
- stdio when `ASTER_MCP_STDIO_ENABLED=true`

HTTP headers and stdio environment values are encrypted and are never returned by the API. Discovered tools start disabled, are not copied to new conversations, and require confirmation by default.

Stdio commands run inside the API container. The executable and every required file must exist there.

## Approved memory

Memory is explicit owner-controlled data.

- A memory may be global or scoped to one persona.
- Manual and imported memories are approved immediately because the owner supplied them.
- Utility-model extraction creates pending suggestions only.
- Suggestions must be accepted or rejected manually.
- Memories can be edited, disabled, deleted, imported, exported, and reindexed.
- Persona-scoped memory is considered only when the conversation uses that persona.

Memory suggestions deliberately reject transient tasks, credentials, assistant claims, speculative traits, and instructions found inside documents or tool results.

## Private knowledge and RAG

Create collections under **Settings → Memory & Knowledge**, then upload documents.

Supported inputs:

- plain text, Markdown, reStructuredText, and logs
- JSON, JSONL, CSV, TSV, XML, YAML, TOML, and INI
- HTML with scripts and styles excluded from visible text
- PDFs containing extractable text

Scanned PDFs require OCR outside Aster.

Aster stores extracted text, a SHA-256 content hash, deterministic chunks, and optional vectors. Original uploads are not exposed through a public download route.

Retrieval behavior:

- lexical retrieval is always available;
- an optional embedding model adds semantic scoring;
- embeddings are stored as JSON vectors in PostgreSQL without pgvector;
- embedding failures keep lexical indexing and retrieval available;
- vectors created by a different model are ignored until reindexing;
- memory and document context enter the model as untrusted developer data;
- document-dependent claims use visible `[D#]` labels;
- every selected source is persisted against the assistant message and can be expanded in chat.

Collections marked as defaults are copied only to new conversations. Existing conversations are never modified retroactively.

## Images

Open the image panel from the chat composer for an explicit image operation. Aster does not infer image intent from keywords in ordinary messages.

Before the first operation:

1. Select an Image model under **Settings → Models**, or leave Image empty to use a compatible Primary model.
2. Open **Images**.
3. Declare the model's actual generation and editing capabilities.
4. Configure provider defaults only when the provider requires them.

Stage 14 supports:

- generation from a text prompt;
- editing with one or more PNG, JPEG, or WebP inputs when the model allows it;
- an optional image mask when the model allows it;
- normalized size, quality, output format, background, count, and input-fidelity parameters;
- bounded additional provider parameters that cannot replace Aster-controlled fields;
- persistent input and output attachments in the conversation;
- a private gallery with prompt, model, parameters, result metadata, failures, and conversation links;
- restart recovery that marks interrupted operations as failed instead of leaving them running forever.

Uploads and outputs are validated by file signature and dimensions. Private metadata is removed from supported formats before storage. SVG, generic multimodal chat, OCR, audio, video, public media sharing, background generation, and scheduled image jobs are outside Stage 14.

Media bytes are never stored inside chat text or PostgreSQL. The database stores metadata and relationships; the `aster-media` volume stores the files. Media content is available only through authenticated API routes.

## Conversation transfer

- Version 1: basic conversation messages
- Version 2: persona snapshot
- Version 3: portable tool-call history
- Version 4: retrieval flags and local collection names

Version 4 does not export approved memory, document text, chunks, vectors, retrieval source snapshots, or private image bytes. Image turns include an explicit omission note so an imported transcript never pretends the missing binary was transferred.

During import, collection names are matched only against collections that already exist locally.

## Runtime limits

The defaults are intentionally bounded:

```env
ASTER_ENDPOINT_TIMEOUT_SECONDS=30
ASTER_STREAM_TIMEOUT_SECONDS=120
ASTER_MCP_TIMEOUT_SECONDS=30
ASTER_TOOL_MAX_ROUNDS=8
ASTER_TOOL_ARGUMENT_MAX_CHARACTERS=100000
ASTER_TOOL_RESULT_MAX_CHARACTERS=100000
ASTER_MEMORY_MAX_ITEMS=12
ASTER_MEMORY_SUGGESTION_MAX_ITEMS=8
ASTER_RAG_MAX_SOURCES=8
ASTER_RAG_CONTEXT_MAX_CHARACTERS=24000
ASTER_RAG_CANDIDATE_LIMIT=2000
ASTER_DOCUMENT_MAX_BYTES=5000000
ASTER_DOCUMENT_MAX_CHARACTERS=2000000
ASTER_DOCUMENT_CHUNK_CHARACTERS=1600
ASTER_DOCUMENT_CHUNK_OVERLAP=200
ASTER_DOCUMENT_MAX_CHUNKS=2000
ASTER_EMBEDDING_BATCH_SIZE=64
ASTER_MEDIA_ROOT=/var/lib/aster/media
ASTER_IMAGE_TIMEOUT_SECONDS=300
ASTER_IMAGE_UPLOAD_MAX_BYTES=20000000
ASTER_IMAGE_OUTPUT_MAX_BYTES=25000000
ASTER_IMAGE_MAX_PIXELS=40000000
ASTER_IMAGE_MAX_INPUTS=8
ASTER_IMAGE_MAX_OUTPUTS=4
```

Recreate the API container after changing runtime settings:

```bash
docker compose up -d --force-recreate api
```

## Backup and upgrade

Back up the bundled database:

```bash
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > aster-backup.sql
```

Back up private image media separately:

```bash
docker run --rm \
  -v aster_aster-media:/source:ro \
  -v "$PWD":/backup \
  alpine sh -c 'cd /source && tar -czf /backup/aster-media-backup.tar.gz .'
```

The exact Compose volume prefix may differ when the project name is overridden. Confirm it with `docker volume ls` before running the media backup command.

External database deployments should use the backup process provided by their PostgreSQL host.

Upgrade the source checkout:

```bash
git pull --ff-only
docker compose up -d --build
```

The API applies pending migrations automatically.

Migration `0010_memory_and_rag` creates memory, knowledge, chunk, conversation scope, and retrieval provenance tables. Migration `0011_images` creates image profiles, media metadata, operations, inputs, outputs, and message attachments. Existing conversations, messages, personas, endpoints, model caches, tools, retrieval data, and encrypted credentials remain intact.

Changing `ASTER_ENCRYPTION_KEY` without re-encrypting stored credentials makes them unreadable.

## Reset a forgotten password

Run inside the API container:

```bash
docker compose exec api python -m app.cli reset-password
```

The command prompts for the replacement password, updates the Argon2id hash, and revokes every active session.

## Local checks

Web:

```bash
pnpm install
pnpm lint
pnpm typecheck
pnpm build
```

API:

```bash
export ASTER_ENCRYPTION_KEY="development-key-with-at-least-32-characters"
cd apps/api
uv sync --frozen --group dev
uv run ruff check .
uv run pytest
uv run alembic upgrade head
```

Full stack:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
```

## Security baseline

- Passwords are hashed with Argon2id and never stored in plain text.
- Session tokens are random, delivered through `HttpOnly` cookies, and stored only as hashes.
- Unsafe browser requests validate their origin.
- API responses use `Cache-Control: no-store` unless an authenticated media response declares private caching explicitly.
- Endpoint and MCP credentials are encrypted before storage and never returned by APIs.
- Provider response bodies, credentials, passwords, and session tokens are excluded from user errors, logs, fixtures, and documentation.
- Tool results, memory, and retrieved documents are treated as untrusted model context.
- Generated memory suggestions never become approved memory automatically.
- Original uploaded documents are not served through public file routes.
- Image uploads and outputs are bounded, validated, privately stored, and served only through authenticated routes.
- Temporary provider image URLs are never used as durable history.
- The bundled PostgreSQL service is not published to the host.

## Project documentation

- [Changelog](CHANGELOG.md)
- [Project charter](docs/product/project-charter.md)
- [ADR-0012: Tools and MCP](docs/decisions/0012-tools-and-mcp.md)
- [ADR-0013: Personal memory and bounded retrieval](docs/decisions/0013-memory-and-rag.md)
- [ADR-0014: Private image operations and media history](docs/decisions/0014-images.md)

## Status

Stages 1 through 13 have passed automated and real deployment validation. Stage 14 remains in draft until its branch passes automated validation and a real deployment test on the target self-hosted installation.
