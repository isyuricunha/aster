# Changelog

All notable changes to Aster are documented in this file.

## [Unreleased]

### Added

- External PostgreSQL support through `DATABASE_URL`.
- Optional bundled PostgreSQL through the `local-db` Compose profile.
- Runtime configuration for endpoint and stream timeouts.
- Search, availability filtering, and bounded rendering for large model caches.
- Searchable primary, utility, and image model selectors.

### Changed

- The bundled PostgreSQL service no longer publishes port 5432 to the host.
- Endpoint discovery now allows 30 seconds by default.
- The API, web package, and release documentation use version `0.1.0` consistently.

### Fixed

- The Docker web build now receives `NEXT_PUBLIC_ASTER_API_URL`.
- Real endpoints that need more than ten seconds to return a large model list no longer fail prematurely.

## 0.1.0

### Added

- Persistent streamed chat through OpenAI-compatible endpoints.
- Encrypted endpoint API keys and persistent model caching.
- Primary, utility, and image model roles.
- One global persona with system or developer instruction placement.
- Persistent conversations with local title generation.
- Edit and resend with linear tail replacement.
- Assistant response regeneration.
- Explicit response stopping with partial output preservation.
- Interrupted-stream recovery and concurrent-generation protection.
