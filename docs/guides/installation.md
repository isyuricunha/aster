# Installation

Aster is deployed with Docker Compose. The default stack includes the web application, API, worker, and an optional bundled PostgreSQL 17 service.

## Requirements

- Docker Engine or Docker Desktop
- Docker Compose v2
- a persistent host capable of storing PostgreSQL and private media volumes

## Bundled PostgreSQL

Copy the example configuration:

```bash
cp .env.example .env
```

Generate an encryption key:

```bash
openssl rand -hex 32
```

Set the generated value in `.env`:

```env
ASTER_ENCRYPTION_KEY=<generated-value>
```

Keep the default bundled-database settings:

```env
COMPOSE_PROFILES=local-db
POSTGRES_DB=aster
POSTGRES_USER=aster
POSTGRES_PASSWORD=aster
DATABASE_URL=
```

For anything beyond a disposable local installation, replace the example database password before starting the stack.

Start Aster:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

The bundled database is stored in the `postgres-data` volume. Private image and communication attachments are stored in the `aster-media` volume.

## External PostgreSQL

Disable the bundled database profile and provide an async SQLAlchemy URL:

```env
COMPOSE_PROFILES=
DATABASE_URL=postgresql+asyncpg://user:password@database-host:5432/aster
```

Start the same stack:

```bash
docker compose config --quiet
docker compose up -d --build
```

The API applies pending Alembic migrations before becoming ready. The worker waits for API readiness before claiming background work.

## First access

Open the configured web port:

```text
http://localhost:3000
```

When no owner exists, Aster redirects to `/setup`. Creating the first account creates the only owner and permanently closes public sign-up.

Owner credentials do not belong in `.env`.

## LAN access

Set the browser origin and published port as needed:

```env
WEB_PORT=3000
API_PORT=8000
ASTER_CORS_ORIGINS=http://192.168.1.20:3000
ASTER_API_INTERNAL_URL=http://api:8000
ASTER_SESSION_SECURE=false
```

Open the web origin from the remote machine. The browser talks only to the Next.js origin; `/api` is proxied to FastAPI through the Compose network.

## Public HTTPS deployment

Publish the web service behind a trusted reverse proxy or tunnel:

```text
https://aster.example.com/ -> web:3000
```

Use production settings:

```env
APP_ENVIRONMENT=production
ASTER_CORS_ORIGINS=https://aster.example.com
ASTER_API_INTERNAL_URL=http://api:8000
ASTER_SESSION_SECURE=true
```

Do not expose the private API port as the primary public application endpoint. The owner session cookie belongs to the web hostname.

## Health checks

```bash
curl -fsS http://localhost:${API_PORT:-8000}/ready
docker compose exec -T worker test -f /tmp/aster-worker-ready
```

The web service is ready when `http://localhost:${WEB_PORT:-3000}/setup` or the authenticated application responds.

## Updating

Back up the database and media first, then:

```bash
git pull --ff-only origin main
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

See [Backup and upgrade](backup-and-upgrade.md) for restore procedures and encryption-key requirements.
