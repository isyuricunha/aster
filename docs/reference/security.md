# Security reference

Aster uses a single-owner security model. It is not a multi-tenant system and does not provide per-user isolation.

## Authentication

- First access creates one owner and closes public sign-up.
- Passwords are hashed with Argon2id.
- Sessions are random opaque tokens delivered through `HttpOnly` cookies.
- Only session-token hashes are stored.
- Sessions have absolute and idle expiration.
- Password changes and administrative password resets revoke active sessions.
- Login attempts are rate limited.

## Origin and transport

Unsafe authenticated browser requests validate their origin.

For public access:

- terminate HTTPS at a trusted reverse proxy or tunnel;
- set `ASTER_SESSION_SECURE=true`;
- set `ASTER_CORS_ORIGINS` to the exact public web origin;
- expose the web service as the application entry point;
- do not use the FastAPI port as a separate public UI origin.

## Credential storage

Endpoint keys, MCP headers and environment values, communication credentials, and integration credentials are encrypted before storage.

The encryption key comes from `ASTER_ENCRYPTION_KEY`. Losing or changing it makes existing encrypted credentials unreadable.

The application never returns stored secret values after creation. Interfaces expose only whether a secret exists or which credential field names are configured.

## Untrusted content

The following are always data, never authority:

- user and assistant Markdown;
- tool arguments and results;
- memory suggestions;
- approved memory;
- retrieved document text;
- image inputs and provider metadata;
- email and Discord content;
- automation trigger payloads;
- agent observations and external results.

Retrieved or external text cannot promote itself into platform, persona, owner, tool, or permission instructions.

## Markdown and rich email

Chat Markdown does not enable raw HTML or executable scripts.

Rich email HTML is rendered in a sandboxed surface with scripts, forms, navigation, and remote content blocked by default. The plain-text representation remains available.

## Tools and actions

- MCP tools are explicitly discovered and enabled.
- Interactive tools can require owner confirmation.
- Agent tools have immutable per-run scopes and approval policies.
- Communication accounts expose separate read and reply permissions.
- AI-assisted replies remain editable and are never sent automatically.
- Automatic model retries stop before external delivery side effects begin.
- Agent emergency stop blocks new claims and cancels active work.

## Webhooks

Inbound automation webhooks use a public automation UUID and a high-entropy secret header.

The secret is disclosed only when created or rotated and is stored as a SHA-256 hash. It remains in a request header rather than the URL.

Optional delivery identifiers provide idempotent duplicate handling.

## Files and media

- Original documents are not exposed through public file routes.
- Extracted document content is bounded before indexing.
- Images and attachments are validated and stored outside PostgreSQL.
- Private media is available only through authenticated API routes.
- Media responses use private caching and hardened content types.
- SVG and executable document content are not accepted as private image media.

## Deployment checklist

- replace example database credentials;
- generate and preserve a strong encryption key;
- enable HTTPS and secure cookies for public access;
- expose only required ports;
- back up PostgreSQL, private media, and the encryption key;
- keep Docker, PostgreSQL, and the host updated;
- review enabled endpoints, tools, accounts, automations, and agents regularly;
- inspect failed runs and integration deliveries instead of suppressing errors.
