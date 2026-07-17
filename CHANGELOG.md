# Changelog

All notable changes to Aster are documented in this file.

## [Unreleased]

### Added

- Per-model generation profiles for context metadata, output limits, sampling, reasoning effort, and declared chat capabilities.
- Ordered global fallback routing for chat models and endpoints.
- Profile and fallback controls in Models settings.
- Safe Markdown rendering for user and assistant messages.
- GFM tables, task lists, autolinks, strikethrough, and authored line breaks.
- Fenced-code syntax highlighting with per-block copy controls.
- Message copy actions and stable rendering for incomplete streamed code fences.
- Full-history search across conversation titles and message content.
- Versioned JSON conversation export and authenticated import.
- Human-readable Markdown conversation export.
- Inline conversation renaming and keyboard access to history search.
- Shared application frame for chat, model, persona, and account navigation.
- Internal interface icon set and dedicated Aster brand mark.
- Responsive workspace navigation for desktop and mobile layouts.
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

- Unset model-profile values now preserve provider defaults and are omitted from chat requests.
- Eligible model failures may advance to the next fallback only before response content begins.
- Chat content now renders as structured documents instead of plain text.
- Conversation import validates format, version, roles, statuses, metadata, and total size.
- Interface hierarchy now derives from a neutral base, restrained accent, and shared contrast system.
- Sidebar and primary view chrome now form one continuous application frame.
- Navigation, conversation rows, controls, labels, and icons use denser shared alignment rules.
- Surface elevation and selection rely on opacity and tonal separation instead of heavy borders and shadows.
- Chat now uses a compact workspace layout with clearer conversation selection, message hierarchy, contextual actions, and a focused composer.
- Model, persona, account, setup, and sign-in screens now share one dense interface system.
- Forms, endpoint metadata, model browsing, empty states, notices, and responsive behavior use consistent tokens and interaction states.
- Every chat, model, persona, and account route now requires an authenticated owner session.
- The bundled PostgreSQL service no longer publishes port 5432 to the host.
- Endpoint discovery now allows 30 seconds by default.
- The API, web package, and release documentation use version `0.1.0` consistently.

### Fixed

- Fallback routing never combines partial output from different models.
- Authentication and request-validation failures remain visible instead of triggering fallback.
- Incomplete fenced code remains readable while a response is still streaming.
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
