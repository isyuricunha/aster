"use client";

import { useMemo, useState, type FormEvent } from "react";

import type { CachedModel, Persona } from "../../lib/api";
import {
  createAgent,
  deleteAgent,
  runAgent,
  updateAgent,
  type Agent,
  type AgentApprovalPolicy,
  type AgentRun,
  type AgentTriggerType,
  type AgentWrite,
} from "../../lib/agent-api";
import type { CommunicationAccount } from "../../lib/communication-api";
import type { AgentKnowledgeOption, AgentToolOption } from "./page";
import styles from "./agents.module.css";

const MICROS_PER_DOLLAR = 1_000_000;

type Draft = {
  name: string;
  description: string;
  goal: string;
  enabled: boolean;
  paused: boolean;
  triggerType: AgentTriggerType;
  timezone: string;
  schedule: string;
  modelId: string;
  personaId: string;
  memoryEnabled: boolean;
  ragEnabled: boolean;
  maxSteps: number;
  maxModelCalls: number;
  maxToolCalls: number;
  maxRuntimeSeconds: number;
  maxEstimatedTokens: number;
  costLimitUsd: string;
  inputRateUsd: string;
  outputRateUsd: string;
  notifyOnCompletion: boolean;
  notifyOnFailure: boolean;
  tools: Record<string, AgentApprovalPolicy>;
  accounts: Record<
    string,
    { allowRead: boolean; allowReply: boolean; replyApprovalPolicy: "always" | "never" }
  >;
  collections: string[];
};

type WorkingAction = "save" | "run" | "delete";

function blankDraft(): Draft {
  return {
    name: "",
    description: "",
    goal: "",
    enabled: true,
    paused: false,
    triggerType: "manual",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    schedule: "{}",
    modelId: "",
    personaId: "",
    memoryEnabled: false,
    ragEnabled: false,
    maxSteps: 12,
    maxModelCalls: 12,
    maxToolCalls: 20,
    maxRuntimeSeconds: 900,
    maxEstimatedTokens: 100_000,
    costLimitUsd: "",
    inputRateUsd: "",
    outputRateUsd: "",
    notifyOnCompletion: true,
    notifyOnFailure: true,
    tools: {},
    accounts: {},
    collections: [],
  };
}

function dollars(value: number | null): string {
  return value === null ? "" : String(value / MICROS_PER_DOLLAR);
}

function draftFromAgent(agent: Agent): Draft {
  return {
    ...blankDraft(),
    name: agent.name,
    description: agent.description,
    goal: agent.goal,
    enabled: agent.enabled,
    paused: agent.paused,
    triggerType: agent.trigger_type,
    timezone: agent.timezone,
    schedule: JSON.stringify(agent.schedule, null, 2),
    modelId: agent.model_id ?? "",
    personaId: agent.persona_id ?? "",
    memoryEnabled: agent.memory_enabled,
    ragEnabled: agent.rag_enabled,
    maxSteps: agent.max_steps,
    maxModelCalls: agent.max_model_calls,
    maxToolCalls: agent.max_tool_calls,
    maxRuntimeSeconds: agent.max_runtime_seconds,
    maxEstimatedTokens: agent.max_estimated_tokens,
    costLimitUsd: dollars(agent.max_estimated_cost_microusd),
    inputRateUsd: dollars(agent.input_cost_per_million_microusd),
    outputRateUsd: dollars(agent.output_cost_per_million_microusd),
    notifyOnCompletion: agent.notify_on_completion,
    notifyOnFailure: agent.notify_on_failure,
    tools: Object.fromEntries(agent.tools.map((item) => [item.tool_id, item.approval_policy])),
    accounts: Object.fromEntries(
      agent.communication_scopes.map((item) => [
        item.account_id,
        {
          allowRead: item.allow_read,
          allowReply: item.allow_reply,
          replyApprovalPolicy: item.reply_approval_policy,
        },
      ]),
    ),
    collections: agent.knowledge_scopes.map((item) => item.collection_id),
  };
}

function micros(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) throw new Error("Cost values must be positive numbers.");
  return Math.round(parsed * MICROS_PER_DOLLAR);
}

function toPayload(draft: Draft): AgentWrite {
  let schedule: Record<string, unknown> = {};
  if (draft.triggerType !== "manual" && draft.triggerType !== "communication") {
    const parsed = JSON.parse(draft.schedule || "{}") as unknown;
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error("Schedule must be a JSON object.");
    }
    schedule = parsed as Record<string, unknown>;
  }
  const costLimit = micros(draft.costLimitUsd);
  const inputRate = micros(draft.inputRateUsd);
  const outputRate = micros(draft.outputRateUsd);
  if (costLimit !== null && (inputRate === null || outputRate === null)) {
    throw new Error("A cost limit requires both input and output rates.");
  }
  return {
    name: draft.name.trim(),
    description: draft.description.trim(),
    goal: draft.goal.trim(),
    enabled: draft.enabled,
    paused: draft.paused,
    trigger_type: draft.triggerType,
    timezone: draft.timezone.trim() || "UTC",
    schedule,
    model_id: draft.modelId || null,
    persona_id: draft.personaId || null,
    use_default_persona: false,
    memory_enabled: draft.memoryEnabled,
    rag_enabled: draft.ragEnabled,
    max_steps: draft.maxSteps,
    max_model_calls: draft.maxModelCalls,
    max_tool_calls: draft.maxToolCalls,
    max_runtime_seconds: draft.maxRuntimeSeconds,
    max_estimated_tokens: draft.maxEstimatedTokens,
    max_estimated_cost_microusd: costLimit,
    input_cost_per_million_microusd: inputRate,
    output_cost_per_million_microusd: outputRate,
    notify_on_completion: draft.notifyOnCompletion,
    notify_on_failure: draft.notifyOnFailure,
    tools: Object.entries(draft.tools).map(([toolId, approvalPolicy]) => ({
      tool_id: toolId,
      approval_policy: approvalPolicy,
    })),
    communication_scopes: Object.entries(draft.accounts).map(([accountId, item]) => ({
      account_id: accountId,
      allow_read: item.allowRead,
      allow_reply: item.allowReply,
      reply_approval_policy: item.replyApprovalPolicy,
    })),
    knowledge_scopes: draft.collections.map((collectionId) => ({ collection_id: collectionId })),
  };
}

export function AgentEditor({
  agents,
  selectedId,
  models,
  personas,
  tools,
  collections,
  accounts,
  disabled,
  onAgentsChange,
  onRunsChange,
  onSelect,
}: {
  agents: Agent[];
  selectedId: string | null;
  models: CachedModel[];
  personas: Persona[];
  tools: AgentToolOption[];
  collections: AgentKnowledgeOption[];
  accounts: CommunicationAccount[];
  disabled: boolean;
  onAgentsChange: (items: Agent[]) => void;
  onRunsChange: (run: AgentRun) => void;
  onSelect: (id: string | null) => void;
}) {
  const selected = agents.find((item) => item.id === selectedId) ?? null;
  const [creating, setCreating] = useState(agents.length === 0);
  const [draft, setDraft] = useState<Draft>(selected ? draftFromAgent(selected) : blankDraft());
  const [workingAction, setWorkingAction] = useState<WorkingAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const availableModels = useMemo(
    () => models.filter((item) => item.is_available).sort((a, b) => a.model_id.localeCompare(b.model_id)),
    [models],
  );

  function choose(agent: Agent) {
    onSelect(agent.id);
    setCreating(false);
    setDraft(draftFromAgent(agent));
    setError(null);
    setMessage(null);
  }

  function createNew() {
    onSelect(null);
    setCreating(true);
    setDraft(blankDraft());
    setError(null);
    setMessage(null);
  }

  async function refresh(savedId: string) {
    const { listAgents } = await import("../../lib/agent-api");
    const next = await listAgents();
    onAgentsChange(next);
    const saved = next.find((item) => item.id === savedId);
    if (saved) {
      onSelect(saved.id);
      setDraft(draftFromAgent(saved));
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (workingAction || disabled) return;
    setWorkingAction("save");
    setError(null);
    setMessage(null);
    try {
      const payload = toPayload(draft);
      const saved = creating
        ? await createAgent(payload)
        : await updateAgent(selectedId as string, payload);
      await refresh(saved.id);
      setCreating(false);
      setMessage("Agent saved. New runs will use this permission snapshot.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the agent.");
    } finally {
      setWorkingAction(null);
    }
  }

  async function runNow() {
    if (!selected || workingAction || disabled) return;
    setWorkingAction("run");
    setError(null);
    setMessage(null);
    try {
      onRunsChange(await runAgent(selected.id));
      setMessage("Agent run queued.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not queue the agent.");
    } finally {
      setWorkingAction(null);
    }
  }

  async function remove() {
    if (
      !selected ||
      workingAction ||
      disabled ||
      !window.confirm(`Delete agent "${selected.name}"? This cannot be undone.`)
    ) {
      return;
    }
    setWorkingAction("delete");
    setError(null);
    setMessage(null);
    try {
      await deleteAgent(selected.id);
      const next = agents.filter((item) => item.id !== selected.id);
      onAgentsChange(next);
      if (next[0]) choose(next[0]);
      else createNew();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the agent.");
    } finally {
      setWorkingAction(null);
    }
  }

  return (
    <div className={styles.layout}>
      <aside aria-label="Agent definitions" className={styles.sideList}>
        <button
          aria-pressed={creating}
          disabled={Boolean(workingAction)}
          onClick={createNew}
          type="button"
        >
          New agent
        </button>
        {agents.length === 0 ? (
          <p className={styles.sideListEmpty} role="status">No saved agents yet.</p>
        ) : null}
        {agents.map((agent) => (
          <button
            aria-pressed={!creating && selected?.id === agent.id}
            data-selected={!creating && selected?.id === agent.id}
            disabled={Boolean(workingAction)}
            key={agent.id}
            onClick={() => choose(agent)}
            type="button"
          >
            <strong>{agent.name}</strong>
            <span className={styles.itemMeta}>
              {agent.paused ? "paused" : agent.enabled ? agent.trigger_type : "disabled"}
            </span>
          </button>
        ))}
      </aside>

      <form
        aria-busy={Boolean(workingAction)}
        aria-labelledby="agent-editor-title"
        className={`${styles.editor} ${styles.form}`}
        onSubmit={(event) => void save(event)}
      >
        <header className={styles.editorHeader}>
          <div>
            <p>{creating ? "New agent" : "Agent definition"}</p>
            <h2 id="agent-editor-title">{draft.name || "Untitled agent"}</h2>
            <span className={styles.muted}>Permissions and budgets are frozen when each run is queued.</span>
          </div>
          <div className={styles.headerActions}>
            {!creating ? (
              <button disabled={Boolean(workingAction) || disabled} onClick={() => void runNow()} type="button">
                {workingAction === "run" ? "Queueing run…" : "Run now"}
              </button>
            ) : null}
            {!creating ? (
              <button
                className={styles.danger}
                disabled={Boolean(workingAction) || disabled}
                onClick={() => void remove()}
                type="button"
              >
                {workingAction === "delete" ? "Deleting agent…" : "Delete agent"}
              </button>
            ) : null}
            <button className={styles.primary} disabled={Boolean(workingAction) || disabled} type="submit">
              {workingAction === "save" ? "Saving agent…" : "Save agent"}
            </button>
          </div>
        </header>

        {error ? <div className={styles.error} role="alert">{error}</div> : null}
        {message ? <div className={styles.success} role="status">{message}</div> : null}
        {disabled ? <div className={styles.warning} role="status">The emergency stop is active. New runs and agent changes are blocked in this interface.</div> : null}

        <fieldset className={styles.editorFields} disabled={Boolean(workingAction) || disabled}>

        <section className={styles.section}>
          <div className={styles.sectionTitle}><p>Identity</p><h3>Goal and execution state</h3></div>
          <div className={styles.gridTwo}>
            <label>Name<input required maxLength={160} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
            <label>Description<input maxLength={500} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
          </div>
          <label>Persistent goal<textarea required rows={6} value={draft.goal} onChange={(event) => setDraft({ ...draft, goal: event.target.value })} /></label>
          <div className={styles.gridThree}>
            <label className={styles.check}><input checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} type="checkbox" /> Enabled</label>
            <label className={styles.check}><input checked={draft.paused} onChange={(event) => setDraft({ ...draft, paused: event.target.checked })} type="checkbox" /> Pause future runs</label>
            <label>Trigger<select value={draft.triggerType} onChange={(event) => setDraft({ ...draft, triggerType: event.target.value as AgentTriggerType })}><option value="manual">Manual only</option><option value="once">One time</option><option value="interval">Interval</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="communication">Communication event</option></select></label>
          </div>
          {draft.triggerType !== "manual" && draft.triggerType !== "communication" ? (
            <div className={styles.gridTwo}>
              <label>Timezone<input value={draft.timezone} onChange={(event) => setDraft({ ...draft, timezone: event.target.value })} /></label>
              <label>Schedule JSON<textarea rows={5} value={draft.schedule} onChange={(event) => setDraft({ ...draft, schedule: event.target.value })} /></label>
            </div>
          ) : null}
        </section>

        <section className={styles.section}>
          <div className={styles.sectionTitle}><p>Context</p><h3>Model, persona, memory, and knowledge</h3></div>
          <div className={styles.gridTwo}>
            <label>Model<select value={draft.modelId} onChange={(event) => setDraft({ ...draft, modelId: event.target.value })}><option value="">Primary routing</option>{availableModels.map((model) => <option key={model.id} value={model.id}>{model.endpoint_name} / {model.model_id}</option>)}</select></label>
            <label>Persona<select value={draft.personaId} onChange={(event) => setDraft({ ...draft, personaId: event.target.value })}><option value="">No persona</option>{personas.filter((item) => item.enabled).map((persona) => <option key={persona.id} value={persona.id}>{persona.name}</option>)}</select></label>
          </div>
          <div className={styles.gridTwo}>
            <label className={styles.check}><input checked={draft.memoryEnabled} onChange={(event) => setDraft({ ...draft, memoryEnabled: event.target.checked })} type="checkbox" /> Use approved memory</label>
            <label className={styles.check}><input checked={draft.ragEnabled} onChange={(event) => setDraft({ ...draft, ragEnabled: event.target.checked })} type="checkbox" /> Use selected knowledge collections</label>
          </div>
          <div className={styles.optionList}>
            {collections.length === 0 ? (
              <div className={styles.empty} role="status">No knowledge collections are available.</div>
            ) : null}
            {collections.map((collection) => (
              <label className={styles.option} key={collection.id}>
                <input checked={draft.collections.includes(collection.id)} disabled={!collection.enabled} onChange={(event) => setDraft({ ...draft, collections: event.target.checked ? [...draft.collections, collection.id] : draft.collections.filter((id) => id !== collection.id) })} type="checkbox" />
                <span><strong>{collection.name}</strong><span className={styles.itemMeta}>{collection.document_count} documents · {collection.description || "No description"}</span></span>
              </label>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionTitle}><p>Budgets</p><h3>Hard execution limits</h3></div>
          <div className={styles.gridThree}>
            <label>Maximum steps<input min={1} max={100} type="number" value={draft.maxSteps} onChange={(event) => setDraft({ ...draft, maxSteps: Number(event.target.value) })} /></label>
            <label>Maximum model calls<input min={1} max={100} type="number" value={draft.maxModelCalls} onChange={(event) => setDraft({ ...draft, maxModelCalls: Number(event.target.value) })} /></label>
            <label>Maximum actions<input min={0} max={500} type="number" value={draft.maxToolCalls} onChange={(event) => setDraft({ ...draft, maxToolCalls: Number(event.target.value) })} /></label>
            <label>Runtime seconds<input min={10} max={86400} type="number" value={draft.maxRuntimeSeconds} onChange={(event) => setDraft({ ...draft, maxRuntimeSeconds: Number(event.target.value) })} /></label>
            <label>Estimated token limit<input min={100} max={10000000} type="number" value={draft.maxEstimatedTokens} onChange={(event) => setDraft({ ...draft, maxEstimatedTokens: Number(event.target.value) })} /></label>
            <label>Estimated cost limit (USD)<input min={0} step="0.000001" type="number" value={draft.costLimitUsd} onChange={(event) => setDraft({ ...draft, costLimitUsd: event.target.value })} placeholder="Optional" /></label>
            <label>Input rate / 1M tokens (USD)<input min={0} step="0.000001" type="number" value={draft.inputRateUsd} onChange={(event) => setDraft({ ...draft, inputRateUsd: event.target.value })} placeholder="Required for cost limit" /></label>
            <label>Output rate / 1M tokens (USD)<input min={0} step="0.000001" type="number" value={draft.outputRateUsd} onChange={(event) => setDraft({ ...draft, outputRateUsd: event.target.value })} placeholder="Required for cost limit" /></label>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionTitle}><p>Tools</p><h3>Explicit MCP capabilities</h3></div>
          <div className={styles.optionList}>
            {tools.length === 0 ? (
              <div className={styles.empty} role="status">No tools are available.</div>
            ) : null}
            {tools.map((tool) => {
              const policy = draft.tools[tool.id];
              const toolLabel = `${tool.server_name} ${tool.name}`;
              return (
                <div className={styles.option} key={tool.id}>
                  <label className={styles.optionToggle}>
                    <input
                      aria-label={`Enable ${toolLabel}`}
                      checked={Boolean(policy)}
                      disabled={!tool.enabled || !tool.is_available}
                      onChange={(event) => { const next = { ...draft.tools }; if (event.target.checked) next[tool.id] = "always"; else delete next[tool.id]; setDraft({ ...draft, tools: next }); }}
                      type="checkbox"
                    />
                    <span><strong>{tool.server_name} · {tool.name}</strong><span className={styles.itemMeta}>{tool.description || tool.public_name}</span></span>
                  </label>
                  <select aria-label={`Approval policy for ${toolLabel}`} disabled={!policy} value={policy ?? "always"} onChange={(event) => setDraft({ ...draft, tools: { ...draft.tools, [tool.id]: event.target.value as AgentApprovalPolicy } })}><option value="always">Always approve</option><option value="tool_default">Tool default</option><option value="never">No approval</option></select>
                </div>
              );
            })}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionTitle}><p>Communications</p><h3>Readable and writable accounts</h3></div>
          <div className={styles.optionList}>
            {accounts.length === 0 ? (
              <div className={styles.empty} role="status">No communication accounts are available.</div>
            ) : null}
            {accounts.map((account) => {
              const scope = draft.accounts[account.id];
              return (
                <div className={styles.option} key={account.id}>
                  <label className={styles.optionToggle}>
                    <input aria-label={`Allow access to ${account.name}`} checked={Boolean(scope)} onChange={(event) => { const next = { ...draft.accounts }; if (event.target.checked) next[account.id] = { allowRead: true, allowReply: false, replyApprovalPolicy: "always" }; else delete next[account.id]; setDraft({ ...draft, accounts: next }); }} type="checkbox" />
                    <span><strong>{account.name}</strong><span className={styles.itemMeta}>{account.kind} · {account.enabled ? "enabled" : "disabled"}</span></span>
                  </label>
                  {scope ? <div><label className={styles.check}><input aria-label={`Allow replies from ${account.name}`} checked={scope.allowReply} onChange={(event) => setDraft({ ...draft, accounts: { ...draft.accounts, [account.id]: { ...scope, allowReply: event.target.checked } } })} type="checkbox" /> Allow replies</label><select aria-label={`Reply approval policy for ${account.name}`} disabled={!scope.allowReply} value={scope.replyApprovalPolicy} onChange={(event) => setDraft({ ...draft, accounts: { ...draft.accounts, [account.id]: { ...scope, replyApprovalPolicy: event.target.value as "always" | "never" } } })}><option value="always">Always approve replies</option><option value="never">No approval</option></select></div> : null}
                </div>
              );
            })}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionTitle}><p>Notifications</p><h3>Owner visibility</h3></div>
          <div className={styles.gridTwo}>
            <label className={styles.check}><input checked={draft.notifyOnCompletion} onChange={(event) => setDraft({ ...draft, notifyOnCompletion: event.target.checked })} type="checkbox" /> Notify on completion</label>
            <label className={styles.check}><input checked={draft.notifyOnFailure} onChange={(event) => setDraft({ ...draft, notifyOnFailure: event.target.checked })} type="checkbox" /> Notify on failure</label>
          </div>
        </section>
        </fieldset>
      </form>
    </div>
  );
}
