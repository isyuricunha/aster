# Communication Hub

The Communication Hub provides private email and Discord inboxes inside Aster.

Inbound messages are persisted before automations or agents process them. Models, automations, and agents receive no implicit account access or reply authority.

## Runtime configuration

```env
ASTER_COMMUNICATION_LEASE_SECONDS=180
ASTER_COMMUNICATION_MESSAGE_MAX_CHARACTERS=200000
ASTER_COMMUNICATION_ATTACHMENT_MAX_BYTES=15000000
ASTER_COMMUNICATION_MAX_ATTACHMENTS=16
```

The API and worker must mount the same `ASTER_MEDIA_ROOT`. The default Compose stack mounts `aster-media` at `/var/lib/aster/media` for both services.

## IMAP accounts

Open **Communications → Accounts**, create an **Email inbox · IMAP** account, and provide:

- IMAP host and port;
- plain, STARTTLS, or TLS/SSL transport;
- folder name, normally `INBOX`;
- username and password or application password;
- polling interval.

Credentials are encrypted and are never returned by the API.

The first synchronization imports a bounded recent window. Later synchronization advances a durable UID cursor per folder.

## Email reading

Email threads provide:

- chronological messages;
- sender and recipient metadata;
- unread state;
- search and filters;
- private attachment downloads;
- plain-text content;
- sandboxed rich HTML rendering.

Rich HTML runs without scripts, forms, top-level navigation, or remote content by default.

## Email replies

Inbound email remains read-only until the account is linked to an enabled SMTP integration from **Automations → Integrations**.

Manual replies preserve `In-Reply-To` and `References` headers when available.

Aster can generate a bounded AI-assisted reply draft. The draft remains editable and is never sent automatically. Sending always requires an explicit owner action.

## Discord accounts

Create a Discord bot account and provide:

- bot token;
- one or more allowed channel IDs;
- optional local channel labels;
- polling interval.

The connection test resolves the bot through `/users/@me`. Synchronization reads only configured channel IDs and advances a durable cursor per channel.

Messages authored by the configured bot are ignored during inbound polling.

Manual and AI-assisted Discord replies permanently disable mention parsing:

```json
{"allowed_mentions":{"parse":[]}}
```

## Inbox

The Inbox supports:

- account and source filters;
- email and Discord filters;
- unread-only filtering;
- subject, sender, and content search;
- persisted threads and chronological messages;
- private attachments;
- manual replies;
- AI-assisted editable drafts;
- marking threads read.

## Communication-triggered automations

Create an automation with the **Communication message** trigger. It remains idle until an explicit rule is added under **Communications → Rules**.

A rule binds one account to one automation and may require:

- a sender glob;
- one or more source IDs;
- body text;
- a Discord bot mention.

Every configured condition must match. A matching message queues one idempotent run with a bounded persisted snapshot.

Communication-triggered automations do not inherit permission to send a reply.

## Agent access

Agents receive account access through immutable per-run scopes.

Read and Reply are separate permissions. Reply access may still require owner approval for every proposed message.

Message content cannot expand agent permissions or change the saved goal.

## Operational checks

```bash
curl -fsS http://localhost:${API_PORT:-8000}/ready
docker compose exec -T worker test -f /tmp/aster-worker-ready
docker compose exec -T api alembic current
```

For synchronization or reply failures:

```bash
docker compose logs --tail=300 api worker web postgres
```

Verify one account at a time: test the connection, enable it, synchronize twice, confirm deduplication, inspect a thread, download an attachment, and send one explicit reply through the configured transport.
