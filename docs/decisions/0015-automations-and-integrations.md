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
- inbound webhook execution through a public automation UUID plus a secret request header.

Timezone-aware schedules use the standard library `zoneinfo` database. Cron expressions, calendar-event triggers, email inbox polling, and arbitrary conditional graphs are deferred.

When Aster returns after downtime, each overdue automation receives at most one catch-up run. Its schedule then advances directly to the next future occurrence instead of replaying every missed interval.

### Execution

An automation stores a prompt, an optional frozen persona snapshot, an optional explicit chat model, retry limits, timeout limits, and delivery bindings. When no model is selected, normal Primary and fallback routing is used.

Automation model calls are bounded text generations. Stage 15 does not execute MCP tools in the background and does not create hidden chat conversations. The exact prompt, trigger payload, selected model, output, error, attempts, and timestamps remain attached to the automation run.

### Integrations

Stage 15 provides explicit owner-configured connections for:

- SMTP email delivery;
- CalDAV-compatible calendar event creation;
- outbound HTTP webhooks.

Secrets and sensitive headers are encrypted before storage and are never placed in model context or returned by integration APIs. Connection tests are explicit and never run automatically during normal page rendering.

### Inbound webhooks

An inbound webhook uses:

```text
POST /api/webhooks/{automation_id}
X-Aster-Webhook-Token: <secret>
```

The automation UUID is not a secret. The high-entropy token is returned only when an endpoint is created or rotated; only its SHA-256 hash is stored. Keeping the token in a header prevents normal reverse-proxy and application access logs from recording it as part of the request path.

Webhook request bodies are bounded. Delivery records persist a caller-supplied `X-Aster-Delivery` or `Idempotency-Key` value when present. Repeating that value for the same automation returns a duplicate response without creating another run. Requests without a delivery identifier are accepted as independent events.

### Notifications

Aster stores private in-app notifications for automation success and failure according to each automation policy. Notifications can be marked read or deleted and link back to the automation and run.

### Reliability

- scheduled occurrences use unique occurrence keys;
- webhook deliveries use persisted idempotency keys when callers provide one;
- queued runs are claimed with `FOR UPDATE SKIP LOCKED` where supported;
- running work holds an expiring lease renewed by heartbeat;
- a worker that loses its lease stops the local execution;
- expired leases are recovered;
- model retries are delayed and bounded;
- retries stop before external delivery begins, avoiding repeated side effects;
- model output is durably stored before integrations execute;
- every delivery records its own success or failure;
- disabling an automation prevents new scheduled runs but does not erase history;
- cancelling a queued run never deletes its audit record;
- the worker tolerates database maintenance and migration windows and resumes polling afterward.

## Consequences

The default deployment gains a continuously running worker but no additional datastore. One-time, interval, daily, weekly, webhook, notification, SMTP, CalDAV, and outbound-webhook workflows are available through one coherent history.

The stage intentionally excludes visual workflow graphs, arbitrary multi-step branching, MCP tools in unattended runs, browser automation, agents, inbound email polling, full calendar synchronization, OAuth provider catalogs, SMS, chat-network integrations, public notification feeds, and distributed worker fleets.
