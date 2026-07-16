# ADR-0006: Runtime deployment configuration

## Status

Accepted

## Context

The first real deployment exposed two assumptions that were safe in CI but wrong in normal self-hosted use:

- the Compose stack required its bundled PostgreSQL service even when a database already existed elsewhere;
- endpoint discovery used a fixed ten-second timeout, which was too short for a valid endpoint returning more than one thousand models.

The browser build also needs a public API URL that is different from the internal container URL. `NEXT_PUBLIC_ASTER_API_URL` is compiled into the Next.js client bundle and cannot be changed by restarting the finished image.

## Decision

Aster supports two database modes through the same Compose file.

The bundled PostgreSQL service belongs to the `local-db` profile. `.env.example` enables that profile so the default installation remains one command. When `DATABASE_URL` is empty, the API derives its connection URL from `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

External database deployments disable the profile and set `DATABASE_URL` to a PostgreSQL URL reachable from the API container. An explicit `DATABASE_URL` always takes precedence over the local PostgreSQL settings.

The bundled PostgreSQL service does not publish port 5432 to the host. It remains reachable by other services on the Compose network.

Endpoint and stream timeouts are runtime settings:

- `ASTER_ENDPOINT_TIMEOUT_SECONDS`, default `30`;
- `ASTER_STREAM_TIMEOUT_SECONDS`, default `120`.

The public browser API URL remains a build argument. Changing `NEXT_PUBLIC_ASTER_API_URL` requires rebuilding the web image. `ASTER_API_INTERNAL_URL` remains a runtime value used by server-side web requests.

Large model caches remain complete in the API and database. The web interface filters and renders them in bounded batches instead of mounting the full cache at once.

## Consequences

A new local installation still starts with `docker compose up --build` after copying `.env.example`.

Existing local installations keep using their current `POSTGRES_*` values without duplicating credentials inside `DATABASE_URL`.

An external database installation must keep `COMPOSE_PROFILES` empty and provide `DATABASE_URL`.

The application can handle slow but valid model-list endpoints without forcing every deployment to use the same timeout.

The web image must be rebuilt when its public API origin changes.
