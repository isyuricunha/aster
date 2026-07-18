# Stage 16 — Communication Hub

## Goal

Add private inbound email and Discord communication surfaces without granting models or automations implicit reply authority.

## Accepted scope

### Email

- IMAP accounts with plain, STARTTLS, and TLS/SSL transport modes
- encrypted username and password or application-password storage
- bounded first synchronization and durable UID cursors
- persistent threads, messages, unread state, text, HTML data, and attachments
- manual replies through an explicitly linked SMTP integration
- `In-Reply-To` and `References` preservation when source headers are available

### Discord

- encrypted bot-token storage
- explicit channel-ID allowlists
- bot identity validation before synchronization
- durable message cursors per channel
- persistent messages, threads, attachments, and participants
- manual channel replies
- mention parsing always disabled with `allowed_mentions: {"parse": []}`

### Automations

- `communication` as a first-class trigger and run source
- separate allowlist rules for account, sender, source, body text, and optional Discord bot mention
- one idempotent run per matching message and automation
- persisted, bounded message snapshots treated as untrusted trigger data
- no automatic reply permission

### Operations

- PostgreSQL-backed synchronization leases
- deduplication by external message ID
- shared private media storage between API and worker
- authenticated attachment downloads
- account, thread, message, rule, and run audit history
- migration `0015_communication_hub`

## Explicit exclusions

Stage 16 does not include:

- autonomous email or Discord replies
- unrestricted Discord mentions
- full Discord gateway event handling
- inbox access from ordinary chat without an explicit future tool or agent scope
- provider-specific OAuth flows
- multiple application owners

## Validation

The stage is accepted when:

1. API lint, tests, and offline migration validation pass.
2. Web lint, TypeScript, and production build pass.
3. The bundled and external PostgreSQL Compose configurations remain valid.
4. A legacy database upgrades through `0015_communication_hub`.
5. `/communications` and every communication API require the owner session.
6. Stored account responses never expose credential values.
7. A communication automation remains idle until an enabled rule matches.
8. Repeated synchronization does not duplicate messages or automation runs.
9. The API and worker share the private media volume.
10. Existing chat, tools, memory, images, and automation contracts remain green.

## Next stage

Stage 17 adds Autonomous Agents on top of tools, memory, RAG, automations, and communication events. Agents must receive explicit scopes, budgets, approval policies, and emergency controls. They must not inherit communication reply authority from Stage 16.
