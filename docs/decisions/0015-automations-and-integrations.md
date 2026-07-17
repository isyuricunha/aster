# ADR-0015: Scheduled automations and bounded integrations

## Status

Accepted for Stage 15.

## Context

Aster needs durable one-time and recurring tasks, internal notifications, email delivery, calendar delivery, inbound and outbound webhooks, external integration configuration, and inspectable execution history. These capabilities must survive restarts and avoid duplicate execution without introducing Redis, Celery, RabbitMQ, a visual workflow engine, or autonomous agents.

Background execution also changes the trust boundary. A model call may happen while the owner is not present, integrations contain credentials, webhook requests are untrusted input, and retries can accidentally repeat side effects.

## Decision

Stage 15 adds one PostgreSQL-backed automation subsystem and one worker process using the same API image.

The default Compose stack becomes:

```text
web
api
worker
postgres
```

PostgreSQL stores automation definitions, schedules, queued runs, leases, retry state, notifications, integration metadata, webhook deliveries, and audit history. The worker claims due work with row locks and expiring leases. Redis and a separate queue are not required.

### Triggers

The bounded trigger set is:

- one-time execution at an absolute instant;
- fixed interval execution;
- daily execution at a local wall-clock time;
- weekly execution at a local weekday and wall-clock time;
- inbound webhook execution through a random endpoint token.

Timezone-aware schedules use the standard library `zoneinfo` database. Cron expressions, calendar-event triggers, email inbox polling, and arbitrary conditional graphs are deferred.

### Execution

An automation stores a prompt, an optional frozen persona snapshot, an optional explicit chat model, retry limits, timeout limits, and delivery bindings. When no model is selected, normal Primary and fallback routing is used.

Automation model calls are bounded text generations. Stage 15 does not execute MCP tools in the background and does not create hidden chat conversations. The exact prompt, trigger payload, selected model, output, error, attempts, and timestamps remain attached to the automation run.

### Integrations

Stage 15 provides explicit owner-configured connections for:

- SMTP email delivery;
- CalDAV-compatible calendar event creation;
- outbound HTTP webhooks.

Secrets and sensitive headers are encrypted before storage and are never placed in model context. Connection tests are explicit and never run automatically during normal page rendering.

Inbound webhooks use a high-entropy token, bounded request bodies, persisted delivery records, and idempotency keys. The token is returned only when an endpoint is created or rotated; only its hash is stored.

### Notifications

Aster stores private in-app notifications for automation success and failure according to each automation policy. Notifications can be marked read or deleted and link back to the automation and run.

### Reliability

- scheduled occurrences use unique occurrence keys;
- webhook deliveries use persisted idempotency keys;
- queued runs are claimed with `FOR UPDATE SKIP LOCKED` where supported;
- running work holds an expiring lease renewed by heartbeat;
- expired leases are recovered;
- retries are delayed and bounded;
- integrations execute only after model output is durably stored;
- every delivery records its own success or failure;
- disabling an automation prevents new scheduled runs but does not erase history;
- cancelling a queued run never deletes its audit record.

## Consequences

The default deployment gains a continuously running worker but no additional datastore. One-time, interval, daily, weekly, webhook, notification, SMTP, CalDAV, and outbound-webhook workflows are available through one coherent history.

The stage intentionally excludes visual workflow graphs, arbitrary multi-step branching, MCP tools in unattended runs, browser automation, agents, inbound email polling, full calendar synchronization, OAuth provider catalogs, SMS, chat-network integrations, public notification feeds, and distributed worker fleets.