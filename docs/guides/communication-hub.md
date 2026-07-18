# Communication Hub

The Communication Hub provides private email and Discord inboxes inside Aster. It stores inbound messages before any automation runs and does not grant models implicit access to communication accounts.

## Runtime configuration

The default values are suitable for most self-hosted installations:

```env
ASTER_COMMUNICATION_LEASE_SECONDS=180
ASTER_COMMUNICATION_MESSAGE_MAX_CHARACTERS=200000
ASTER_COMMUNICATION_ATTACHMENT_MAX_BYTES=15000000
ASTER_COMMUNICATION_MAX_ATTACHMENTS=16
```

The API and worker must mount the same `ASTER_MEDIA_ROOT`. The default Compose stack mounts the shared `aster-media` volume at `/var/lib/aster/media` for both services.

## IMAP accounts

Open **Communications → Accounts**, create an **Email inbox · IMAP** account, and provide:

- IMAP host and port
- plain, STARTTLS, or TLS/SSL transport
- folder name, normally `INBOX`
- username and password or application password
- polling interval

Aster stores credentials encrypted and returns only the credential field names. The first synchronization imports a bounded recent window. Later synchronizations use the durable folder UID cursor.

### Email replies

Inbound email is read-only until the account is linked to an enabled SMTP integration from **Automations → Integrations**. Manual replies preserve `In-Reply-To` and `References` headers when the source message provides them.

Stage 16 does not expose automatic email replies.

## Discord accounts

Create a Discord bot account and provide:

- bot token
- one or more allowed channel IDs
- optional local labels for those channels
- polling interval

The connection test resolves the bot identity through `/users/@me`. Synchronization requests messages only from the configured channel IDs and advances a durable cursor per channel.

Messages authored by the configured bot are ignored during inbound polling. Every manual reply disables Discord mention parsing:

```json
{"allowed_mentions":{"parse":[]}}
```

There is no setting that enables unrestricted mentions.

## Inbox

The Inbox supports:

- account and channel filters
- email and Discord filters
- unread-only filtering
- subject, sender, and message search
- persisted threads and chronological messages
- private attachment downloads
- manual replies
- marking threads read

HTML email bodies are retained as untrusted data but are not rendered as trusted HTML.

## Communication automations

Create an automation with the **Communication message** trigger. It has no schedule and cannot run from inbound messages until an explicit rule is added under **Communications → Rules**.

A rule selects one communication account and one communication-triggered automation. Optional conditions include:

- sender glob pattern, such as `*@example.com`
- source IDs, such as IMAP folders, email addresses, Discord channels, or Discord user IDs
- required body text
- required Discord bot mention

Every configured condition must match. A matching message queues one idempotent run with a bounded persisted message snapshot. The snapshot is untrusted trigger data, not system authority.

Communication automations do not inherit permission to send a reply.

## Operational checks

After deployment:

```bash
docker compose exec -T api alembic current
docker compose exec -T worker test -f /tmp/aster-worker-ready && echo "Worker ready"
```

Expected migration:

```text
0015_communication_hub (head)
```

Then verify:

1. `/communications` loads after authentication.
2. An account can be created with synchronization disabled.
3. **Test** validates the external account.
4. **Sync now** imports messages without duplicating them on a second run.
5. A communication automation remains idle without a matching rule.
6. A matching allowed message creates exactly one automation run.
7. A manual reply appears as an outbound message in the thread.

For failures, inspect both API and worker logs:

```bash
docker compose logs --tail=200 api worker web postgres
```
