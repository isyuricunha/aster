# ADR-0017: Communication Hub

## Status

Accepted for Stage 16.

## Context

Aster already had outbound SMTP, CalDAV, and webhook deliveries, but it had no durable inbound communication surface. Email and Discord messages could not be read, searched, threaded, or used as explicit automation events inside the private workspace.

The communication layer must preserve Aster's single-owner, self-hosted security model. Receiving a message must not silently grant the model access to an account, and inbound content must never become system authority. External services also require durable cursors and deduplication because polling can repeat data after restarts or network failures.

## Decision

Aster adds a private Communication Hub with two account kinds:

- IMAP email accounts
- Discord bot accounts restricted to explicitly configured channel IDs

The existing automation worker also polls communication accounts. PostgreSQL stores account state, source cursors, threads, messages, attachment metadata, and routing rules. Attachments use the existing private media volume instead of database binary columns.

### Email

IMAP supports plain, STARTTLS, and TLS connections. Each folder uses a durable UID cursor. A bounded first synchronization imports only the latest messages, while later synchronizations request UIDs after the stored cursor.

Text and HTML bodies are extracted deterministically. HTML is retained as data but is not rendered as trusted markup. Manual replies use an explicitly linked SMTP integration and preserve `In-Reply-To` and `References` headers when available.

### Discord

Discord uses a bot token and polls only explicitly listed channel IDs. Per-channel message IDs are durable cursors. Messages authored by the configured bot are ignored during inbound synchronization to prevent reply loops.

Every manual Discord reply sends:

```json
{"allowed_mentions":{"parse":[]}}
```

Aster does not expose a configuration that can enable unrestricted mentions.

### Automation events

`communication` is a first-class automation trigger and run source. A communication automation has no schedule and cannot be queued merely because an account received a message.

A separate enabled routing rule must match the account and every configured condition:

- sender pattern
- source ID allowlist
- body text
- optional Discord bot mention

A matching message queues one run per automation through a deterministic occurrence key. The trigger payload is a bounded snapshot of the persisted message and is treated as untrusted user data by automation execution.

### Replies and authority

Replies are manual only in Stage 16. Communication automations do not inherit permission to send email or Discord messages. Any later autonomous reply capability must define a separate approval and policy boundary.

### Credentials and storage

Account credentials are encrypted with the existing Aster encryption key. API responses expose only credential field names. Attachment routes require the authenticated owner session and return private no-store responses.

Account synchronization uses expiring PostgreSQL leases and `FOR UPDATE SKIP LOCKED`, allowing multiple workers without duplicate ownership. External message IDs and automation occurrence keys provide idempotency after retries and restarts.

## Consequences

- The default Compose stack does not gain Redis, a message broker, or another worker service.
- The automation worker mounts the same private media volume as the API.
- Email reply support depends on an existing enabled SMTP integration.
- Discord is intentionally channel-allowlist based rather than a full gateway client.
- Stage 17 agents may consume communication events, but they do not receive implicit account or reply authority from this stage.
