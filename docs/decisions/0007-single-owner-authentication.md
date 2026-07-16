# ADR-0007: Single-owner authentication

## Status

Accepted

## Context

Aster is a single-user, self-hosted application, but the first MVP did not include application authentication. That was acceptable on a trusted LAN and unacceptable for direct remote access. HTTPS protects traffic in transit; it does not stop an unauthenticated visitor from opening conversations, changing endpoints, or spending model-provider credits.

Declaring the first username and password through environment variables would place human credentials in deployment configuration and make the initial experience unnecessarily operational. Public registration would also conflict with the single-owner product model.

## Decision

Aster creates one owner account through a first-access setup flow.

When no user exists, the web application redirects to `/setup`. The first successful setup transaction creates the owner and closes public setup permanently. Later visitors are redirected to `/login`. No registration endpoint can create a second user.

Passwords use Argon2id with the OWASP baseline of 19 MiB memory, two iterations, and one degree of parallelism. Passwords are hashed independently from `ASTER_ENCRYPTION_KEY`, which continues to protect stored model endpoint credentials.

Authentication uses opaque random session tokens in an `HttpOnly` cookie. Only a SHA-256 digest of each token is stored in PostgreSQL. Sessions have absolute and idle expiration, can be revoked, and are rotated after a password change.

Unsafe browser requests validate the `Origin` header against `ASTER_CORS_ORIGINS`. Login attempts are rate limited in memory for the single API process. API responses are marked `Cache-Control: no-store`.

The browser reaches every application route through the Next.js web origin. Next.js proxies `/api` to FastAPI over the internal network. Remote deployments publish one HTTPS hostname for the web service, keep the API port private, and set `ASTER_SESSION_SECURE=true`.

Password recovery is an administrative operation:

```bash
docker compose exec api python -m app.cli reset-password
```

It changes the owner password and revokes every active session. Aster does not implement email recovery, security questions, or environment-defined owner credentials.

## Consequences

Aster can be exposed through a trusted HTTPS reverse proxy without relying on a separate authentication product.

Every existing installation must complete first sign-up after applying the authentication migration. Existing conversations, endpoints, models, persona settings, and credentials remain unchanged.

The application remains single-user. Invitations, roles, organizations, and per-user data isolation are still out of scope.

A deployment that uses HTTPS must explicitly enable secure cookies. The public reverse proxy must not bypass the Next.js `/api` proxy. The host-only session cookie belongs to the web hostname and is forwarded internally only when Aster calls FastAPI.
