# Autonomous Agents

Stage 17 adds bounded persistent agents to Aster. Agents can plan across multiple model calls, use explicitly selected MCP tools, read explicitly selected communication accounts, propose replies, use approved memory and selected knowledge collections, pause for owner approval, and preserve a complete execution history.

## Runtime configuration

The default values are conservative for one self-hosted worker:

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

The worker remains the same Compose service used by durable automations. It schedules automations and agents, synchronizes communication accounts, dispatches communication events, and executes one claimed run at a time.

## Creating an agent

Open **Agents → Agents** and define:

- a name and persistent goal
- manual, one-time, interval, daily, weekly, or communication trigger
- optional model and persona
- approved memory access
- selected knowledge collections
- selected MCP tools and approval policies
- selected communication accounts with read and optional reply permissions
- step, model-call, action, runtime, token, and optional cost limits
- notification preferences

Saving an agent does not start it. Use **Run now**, configure a schedule, or add a communication dispatch rule.

## Immutable run scopes

Every queued run freezes its goal, persona, memory setting, knowledge collections, tools, accounts, approval policies, and budgets. Editing an agent changes future runs only.

This means an active or approval-waiting run cannot gain a newly added tool or communication account.

## Tool approval policies

Each MCP tool has one agent-specific policy:

- **Always approve**: every proposed call pauses for the owner.
- **Tool default**: the tool's existing confirmation setting decides.
- **No approval**: the worker may execute the call immediately when it remains inside every other run limit.

Approval is a queue transition. The web request records the decision and returns the run to the worker. It never performs the tool call itself.

## Communication access

Communication accounts expose separate permissions:

- **Read** permits listing and reading persisted threads.
- **Reply** permits proposing or sending replies through that account.

Reply access can still require approval for every message. Email replies continue to use the account's linked SMTP integration. Discord replies continue to disable mention parsing.

Communication messages and thread content are untrusted data. They cannot expand the agent's permissions or override its saved goal.

## Communication event rules

An agent using the **Communication event** trigger stays idle until a rule is created under **Agents → Event rules**.

A rule binds one agent to one readable communication account and can require:

- a sender glob
- one or more source IDs
- body text
- a Discord bot mention

All configured conditions must match. Rules apply only to messages received after the rule was created. The same message can create at most one run for the same agent.

## Budgets

Every run enforces:

- maximum persisted steps
- maximum model calls
- maximum external or internal actions
- runtime deadline
- estimated token limit
- optional estimated cost limit

Cost limits require explicit input and output rates in USD per one million tokens. Aster currently estimates tokens from serialized character counts. These values are operational guardrails, not provider billing records.

## Run history

**Agents → Runs & approvals** shows:

- trigger and immutable goal snapshot
- selected model and persona
- current plan
- usage counters and deadlines
- every model decision
- every action and argument
- untrusted tool or communication results
- pending, approved, denied, or cancelled approvals
- final output or failure

A denied action remains in the timeline so the next model round can choose a different safe path.

## Pausing, resuming, cancelling, and retrying

- **Pause** requests a checkpoint stop. Queued runs pause immediately; running runs pause at the next control boundary.
- **Resume** returns a paused run to the durable queue.
- **Cancel** prevents additional work and cancels pending approvals.
- **Retry** creates a new run and audit trail from a failed or cancelled run.

A worker lease that expires during an active run fails the run. Aster does not automatically replay an uncertain external side effect.

## Emergency stop

The global emergency stop is displayed at the top of the Agents workspace.

Activating it:

- cancels queued, running, paused, and approval-waiting runs
- cancels pending approvals
- blocks manual runs
- blocks schedules and communication dispatches
- prevents the worker from claiming new agent runs

Releasing the stop permits new work but does not resurrect cancelled runs.

## Deployment checks

After deployment:

```bash
docker compose exec -T api alembic current
docker compose exec -T worker test -f /tmp/aster-worker-ready && echo "Worker ready"
```

Expected migration:

```text
0016_autonomous_agents (head)
```

Then verify:

1. `/agents` requires authentication and loads after login.
2. An agent can be saved with no tools or communication accounts.
3. **Run now** creates one queued run.
4. A direct model result completes the run and creates a notification.
5. A tool with **Always approve** pauses before the MCP call.
6. Approving returns the run to the worker and executes the action once.
7. Denying records the decision and allows a different safe path.
8. Editing the agent does not alter a previously queued run's scopes.
9. The emergency stop cancels active work and blocks new runs.
10. A communication rule dispatches only future matching messages.

For failures, inspect the shared worker and API logs:

```bash
docker compose logs --tail=300 api worker web postgres
```
