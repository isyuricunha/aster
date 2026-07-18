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

## Deployment

Back up PostgreSQL before changing branches. The following command applies to the bundled database profile:

```bash
cd ~/github/aster
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > aster-before-stage16.sql
```

Deploy the branch:

```bash
git fetch origin
git switch communication-hub || git switch --track origin/communication-hub
git pull --ff-only origin communication-hub
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Check the migration and worker:

```bash
curl -fsS "http://localhost:${API_PORT:-8000}/ready"
docker compose exec -T api alembic current
docker compose exec -T worker test -f /tmp/aster-worker-ready && echo "Worker ready"
```

Expected migration:

```text
0015_communication_hub (head)
```

## Real deployment validation

Verify the stage with one account at a time:

1. Open `/communications` after authentication.
2. Create an account with synchronization disabled.
3. Run **Test** and confirm the remote identity or mailbox connection.
4. Enable the account and run **Sync now**.
5. Run synchronization again and confirm that messages are not duplicated.
6. Open a thread, mark it read, and download one attachment when available.
7. For email, link an SMTP integration and send one manual reply.
8. For Discord, send one manual reply and confirm that no mentions are expanded unexpectedly.
9. Create a communication-triggered automation without a rule and confirm that it remains idle.
10. Add a restrictive rule and confirm that one matching message creates exactly one run.

For failures, inspect all services involved in polling, storage, rendering, and background execution:

```bash
docker compose logs --tail=200 api worker web postgres
```
