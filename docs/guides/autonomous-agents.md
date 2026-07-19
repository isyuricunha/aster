# Autonomous agents

Aster agents are bounded persistent workers.

They can plan across multiple model calls, use explicitly selected MCP tools, read explicitly selected communication accounts, propose or send approved replies, use approved memory and selected collections, pause for owner approval, and preserve a complete execution history.

## Runtime configuration

```env
ASTER_AGENT_LEASE_SECONDS=180
ASTER_AGENT_HEARTBEAT_SECONDS=45
ASTER_AGENT_SCHEDULER_BATCH_SIZE=25
ASTER_AGENT_DISPATCH_BATCH_SIZE=100
ASTER_AGENT_OUTPUT_MAX_CHARACTERS=100000
ASTER_AGENT_HISTORY_MAX_CHARACTERS=50000
ASTER_AGENT_RETRIEVAL_MAX_CHARACTERS=24000
ASTER_AGENT_LOOP_REPEAT_LIMIT=3
```

The worker is shared with automations and communications. It schedules and claims durable work through PostgreSQL leases.

## Creating an agent

Open **Agents → Agents** and define:

- name and persistent goal;
- manual, one-time, interval, daily, weekly, or communication trigger;
- optional model and persona;
- approved memory access;
- selected knowledge collections;
- selected MCP tools and approval policies;
- selected communication accounts with read and optional reply permission;
- step, model-call, action, runtime, token, and optional cost limits;
- notification preferences.

Saving an agent does not run it. Use **Run now**, configure a schedule, or add a communication event rule.

## Immutable run scopes

Every queued run freezes its:

- goal;
- persona;
- model selection;
- memory setting;
- knowledge collections;
- tools and approval policies;
- communication accounts and permissions;
- budgets and deadline.

Editing the reusable agent changes future runs only. An active or approval-waiting run cannot gain a newly added tool or account.

## Tool approval policies

Each selected MCP tool has an agent-specific policy:

- **Always approve** — every proposed call pauses for the owner.
- **Tool default** — the tool's global confirmation setting decides.
- **No approval** — the worker may execute the call when it remains inside every other run limit.

Approval is a durable queue transition. The web request records the decision and returns the run to the worker; it does not execute the tool itself.

## Communication access

Account permissions are separate:

- **Read** permits listing and reading persisted threads.
- **Reply** permits proposing or sending replies through that account.

Reply access may still require approval for every message.

Email replies use the account's linked SMTP integration. Discord replies keep mention parsing disabled. Communication content remains untrusted and cannot expand permissions.

## Communication event rules

An agent with the **Communication event** trigger remains idle until a rule is created under **Agents → Event rules**.

A rule binds one agent to one readable account and may require:

- sender glob;
- one or more source IDs;
- body text;
- Discord bot mention.

All configured conditions must match. Rules apply only to messages received after the rule was created. One message can create at most one run for the same agent.

## Budgets

Every run enforces:

- maximum persisted steps;
- maximum model calls;
- maximum actions;
- runtime deadline;
- estimated token limit;
- optional estimated cost limit.

Cost limits require explicit input and output rates per one million tokens. Token and cost values are operational estimates, not provider billing records.

## Runs and approvals

**Agents → Runs & approvals** shows:

- trigger and immutable goal snapshot;
- model and persona;
- current plan;
- counters and deadline;
- model decisions;
- actions and arguments;
- tool, retrieval, and communication results;
- pending, approved, denied, and cancelled approvals;
- final output or failure.

A denied action remains in the timeline so the next model round can choose a different safe path.

## Lifecycle controls

- **Pause** requests a checkpoint stop.
- **Resume** returns a paused run to the durable queue.
- **Cancel** blocks additional work and cancels pending approvals.
- **Retry** creates a new run and audit trail from a failed or cancelled run.

A worker lease that expires during an active run fails the run. Aster does not automatically replay an uncertain external side effect.

## Emergency stop

The global emergency stop:

- cancels queued, running, paused, and approval-waiting runs;
- cancels pending approvals;
- blocks manual runs;
- blocks schedules and communication dispatch;
- prevents the worker from claiming new agent runs.

Releasing it permits new work but does not resurrect cancelled runs.

## Operational checks

```bash
docker compose exec -T api alembic current
docker compose exec -T worker test -f /tmp/aster-worker-ready
```

For failures:

```bash
docker compose logs --tail=300 api worker web postgres
```

Validate a direct model run before granting tools or accounts. Then test approval-required tools, denial, immutable scopes, emergency stop, and communication rules independently.
