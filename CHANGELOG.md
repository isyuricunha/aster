# Changelog

All notable changes to Aster are documented in this file.

## [Unreleased]

### Added

- Single-owner authentication with first-access setup.
- Argon2id password hashing.
- Opaque server-side sessions stored as token hashes.
- Login rate limiting, session revocation, and password rotation.
- Administrative password reset through `python -m app.cli reset-password`.
- Account settings for password changes, logout, and revoking other sessions.
- Same-origin browser API proxy through the Next.js web service.
- External PostgreSQL support through `DATABASE_URL`.
- Optional bundled PostgreSQL through the `local-db` Compose profile.
- Runtime configuration for endpoint and stream timeouts.
- Search, availability filtering, and bounded rendering for large model caches.
- Searchable primary, utility, and image model selectors.

### Changed

- Every chat, model, persona, and account route now requires an authenticated owner session.
- The bundled PostgreSQL service no longer publishes port 5432 to the host.
- Endpoint discovery now allows 30 seconds by default.
- The API, web package, and release documentation use version `0.1.0` consistently.

### Fixed

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
