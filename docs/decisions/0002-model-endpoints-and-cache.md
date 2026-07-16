# ADR-0002: Model endpoints and local model cache

Status: Accepted

Date: 2026-07-16

## Context

Aster needs a provider-neutral way to connect to model services before chat and persona composition are implemented. The first stable MVP only needs OpenAI-compatible endpoint registration, model discovery, cached model identifiers, and three global model roles.

The implementation must not depend on a named gateway or model provider. Credentials must not be returned to the web application after they are stored.

## Decision

Aster stores model endpoints in PostgreSQL with:

- a user-defined display name;
- a normalized HTTP or HTTPS base URL;
- an optional Bearer API key encrypted at rest;
- an enabled state.

The API key is encrypted with AES-GCM. The encryption key is derived from `ASTER_ENCRYPTION_KEY`, which is supplied by the deployment and is never stored in the database.

Model discovery calls `GET {base_url}/models` and accepts the standard OpenAI-compatible response shape containing a `data` array with model `id` values.

Discovered model IDs are cached by endpoint. A successful synchronization marks previously discovered entries missing from the latest response as unavailable instead of deleting them. A failed synchronization does not change cached availability. Manually added model IDs remain available across discovery runs.

Aster stores one global preference record with references to cached model entries:

- primary;
- utility;
- image.

Utility resolves to primary when it is not explicitly selected. Image has no automatic fallback in MVP 1 because image-generation capability detection is deferred.

## Consequences

- Endpoint and model combinations cannot become mismatched because preferences reference one cached model entry.
- Deleting an endpoint removes its model cache and clears affected preferences.
- Cached models remain visible during endpoint outages.
- An endpoint without a compatible `/models` route can still be used by adding model IDs manually.
- Rotating `ASTER_ENCRYPTION_KEY` requires re-encrypting stored credentials before the old key is removed. Automated key rotation is deferred.
- Capability discovery, advanced model parameters, routing, and provider-specific behavior remain outside this milestone.
