# ADR-0018: Bounded autonomous agents

## Status

Accepted

## Context

Aster already supports persistent chat, personas, MCP tools, approved memory, private document retrieval, images, durable automations, and inbound communication channels. Autonomous agents must coordinate those capabilities over multiple steps without turning any existing integration into implicit authority.

A chat loop is not a sufficient execution model. Agent work may outlive one request, pause for approval, resume after a worker restart, react to an event, or stop because a budget was exhausted. External actions also create uncertainty: replaying a tool or reply after a worker interruption may duplicate a side effect.

## Decision

Aster represents every agent as a persistent definition and every execution as a durable state machine.

Each agent stores:

- one explicit goal
- one trigger type
- optional model and persona selection
- explicit memory and knowledge settings
- explicit MCP tool scopes
- explicit communication account scopes
- hard step, model-call, action, runtime, token, and optional cost budgets
- completion and failure notification preferences

When a run is enqueued, Aster freezes the goal, persona, context settings, tool scopes, communication scopes, knowledge collections, approval policies, and budgets. Editing the agent affects future runs only.

The existing durable worker schedules and executes both automations and agents. Agent runs use PostgreSQL leases and heartbeats. One worker process executes at most one claimed automation or agent run at a time.

Every run persists:

- trigger data
- the current plan
- model decisions
- proposed actions
- arguments and results
- approval decisions
- usage estimates
- the final output or failure

Model output can update the plan, finish the run, call one explicitly scoped MCP tool, read one explicitly scoped communication account, or propose a reply through an explicitly writable account. The runtime rejects unknown or out-of-scope actions independently of model instructions.

Approval policies are enforced outside the model. Approving an action only returns the run to the durable queue. The HTTP request never performs the external side effect.

A worker lease that expires during an active run fails the run instead of automatically replaying an uncertain external action. Retrying creates a new run with a new audit trail.

Communication-triggered agents require a separate enabled dispatch rule. Rules apply only to messages received after the rule was created. A message and agent pair can create at most one run.

A singleton emergency stop cancels queued, running, paused, and approval-waiting runs, cancels pending approvals, blocks scheduling and dispatch, and prevents workers from claiming new agent runs.

## Safety boundaries

- Agents never inherit every MCP tool.
- Agents never inherit every communication account.
- Read access never implies reply access.
- Reply access never implies approval-free replies.
- Communication messages, retrieval content, trigger payloads, and tool results remain untrusted data.
- HTML email bodies are never promoted to trusted instructions.
- A model can propose only one action per round.
- Repeated identical actions stop the run after the configured threshold.
- Step, model-call, action, runtime, token, and cost limits are enforced outside the model.
- A denied action becomes part of the persisted history so the model can choose a different safe path.
- Unknown action outcomes are not silently replayed.

## Consequences

Autonomous execution remains inspectable and resumable, but it requires more persistence than a stateless agent loop. The immutable run snapshots intentionally duplicate selected configuration so historical runs remain explainable after an agent is edited.

Token and cost accounting is estimated from serialized request and response characters unless a future provider supplies authoritative usage data. Cost enforcement therefore requires explicit per-model rates configured on the agent.

The initial implementation runs agents serially with automations in the existing worker. Later deployments may add controlled concurrency, but concurrency must preserve leases, immutable scopes, approval boundaries, and the no-replay rule for uncertain side effects.
