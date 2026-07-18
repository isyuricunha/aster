"use client";

import { useState, type FormEvent } from "react";

import {
  createAgentCommunicationRule,
  deleteAgentCommunicationRule,
  listAgentCommunicationRules,
  updateAgentCommunicationRule,
  type Agent,
  type AgentCommunicationRule,
  type AgentCommunicationRuleWrite,
} from "../../lib/agent-api";
import type { CommunicationAccount } from "../../lib/communication-api";
import styles from "./agents.module.css";

type Draft = {
  name: string;
  agentId: string;
  accountId: string;
  enabled: boolean;
  senderPattern: string;
  sourceIds: string;
  bodyContains: string;
  requireMention: boolean;
};

function blankDraft(agents: Agent[], accounts: CommunicationAccount[]): Draft {
  return {
    name: "",
    agentId: agents.find((item) => item.trigger_type === "communication")?.id ?? "",
    accountId: accounts[0]?.id ?? "",
    enabled: true,
    senderPattern: "",
    sourceIds: "",
    bodyContains: "",
    requireMention: false,
  };
}

function draftFromRule(rule: AgentCommunicationRule): Draft {
  return {
    name: rule.name,
    agentId: rule.agent_id,
    accountId: rule.account_id,
    enabled: rule.enabled,
    senderPattern: rule.sender_pattern ?? "",
    sourceIds: rule.source_ids.join("\n"),
    bodyContains: rule.body_contains ?? "",
    requireMention: rule.require_mention,
  };
}

function payload(draft: Draft): AgentCommunicationRuleWrite {
  return {
    name: draft.name.trim(),
    agent_id: draft.agentId,
    account_id: draft.accountId,
    enabled: draft.enabled,
    sender_pattern: draft.senderPattern.trim() || null,
    source_ids: draft.sourceIds
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean),
    body_contains: draft.bodyContains.trim() || null,
    require_mention: draft.requireMention,
  };
}

export function RulePanel({
  rules,
  agents,
  accounts,
  onRulesChange,
}: {
  rules: AgentCommunicationRule[];
  agents: Agent[];
  accounts: CommunicationAccount[];
  onRulesChange: (items: AgentCommunicationRule[]) => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(rules[0]?.id ?? null);
  const [creating, setCreating] = useState(rules.length === 0);
  const [draft, setDraft] = useState<Draft>(
    rules[0] ? draftFromRule(rules[0]) : blankDraft(agents, accounts),
  );
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const selected = rules.find((item) => item.id === selectedId) ?? null;
  const communicationAgents = agents.filter((item) => item.trigger_type === "communication");

  function choose(rule: AgentCommunicationRule) {
    setSelectedId(rule.id);
    setCreating(false);
    setDraft(draftFromRule(rule));
    setError(null);
    setMessage(null);
  }

  function createNew() {
    setSelectedId(null);
    setCreating(true);
    setDraft(blankDraft(agents, accounts));
    setError(null);
    setMessage(null);
  }

  async function refresh(savedId?: string) {
    const next = await listAgentCommunicationRules();
    onRulesChange(next);
    const saved = next.find((item) => item.id === savedId);
    if (saved) choose(saved);
    else if (next[0]) choose(next[0]);
    else createNew();
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (working) return;
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      const saved = creating
        ? await createAgentCommunicationRule(payload(draft))
        : await updateAgentCommunicationRule(selectedId as string, payload(draft));
      await refresh(saved.id);
      setMessage("Rule saved. Only future matching messages can dispatch this agent.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the rule.");
    } finally {
      setWorking(false);
    }
  }

  async function remove() {
    if (!selected || working || !window.confirm(`Delete ${selected.name}?`)) return;
    setWorking(true);
    setError(null);
    try {
      await deleteAgentCommunicationRule(selected.id);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the rule.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className={styles.layout}>
      <aside className={styles.sideList}>
        <button onClick={createNew} type="button">New rule</button>
        {rules.map((rule) => (
          <button
            data-selected={!creating && selected?.id === rule.id}
            key={rule.id}
            onClick={() => choose(rule)}
            type="button"
          >
            <strong>{rule.name}</strong>
            <span className={styles.itemMeta}>{rule.agent_name} · {rule.account_name}</span>
          </button>
        ))}
      </aside>

      <form className={`${styles.editor} ${styles.form}`} onSubmit={(event) => void save(event)}>
        <header className={styles.editorHeader}>
          <div>
            <p>{creating ? "New dispatch rule" : "Communication dispatch"}</p>
            <h2>{draft.name || "Untitled rule"}</h2>
            <span className={styles.muted}>A communication-triggered agent remains idle until an explicit rule matches.</span>
          </div>
          <div className={styles.headerActions}>
            {!creating ? <button className={styles.danger} disabled={working} onClick={() => void remove()} type="button">Delete</button> : null}
            <button className={styles.primary} disabled={working} type="submit">{working ? "Saving…" : "Save"}</button>
          </div>
        </header>

        {error ? <div className={styles.error}>{error}</div> : null}
        {message ? <div className={styles.success}>{message}</div> : null}
        {!communicationAgents.length ? <div className={styles.warning}>Create an agent with the Communication event trigger before adding a rule.</div> : null}

        <section className={styles.section}>
          <div className={styles.gridTwo}>
            <label>Name<input required maxLength={160} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label>
            <label className={styles.check}><input checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} type="checkbox" /> Enabled</label>
            <label>Agent<select required value={draft.agentId} onChange={(event) => setDraft({ ...draft, agentId: event.target.value })}><option value="">Select an agent</option>{communicationAgents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></label>
            <label>Account<select required value={draft.accountId} onChange={(event) => setDraft({ ...draft, accountId: event.target.value })}><option value="">Select an account</option>{accounts.map((account) => <option key={account.id} value={account.id}>{account.name} · {account.kind}</option>)}</select></label>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionTitle}><p>Conditions</p><h3>Every configured condition must match</h3></div>
          <div className={styles.gridTwo}>
            <label>Sender glob<input value={draft.senderPattern} onChange={(event) => setDraft({ ...draft, senderPattern: event.target.value })} placeholder="*@example.com" /></label>
            <label>Body contains<input value={draft.bodyContains} onChange={(event) => setDraft({ ...draft, bodyContains: event.target.value })} /></label>
          </div>
          <label>Source IDs<textarea rows={5} value={draft.sourceIds} onChange={(event) => setDraft({ ...draft, sourceIds: event.target.value })} placeholder="One folder, channel, address, or user ID per line" /></label>
          <label className={styles.check}><input checked={draft.requireMention} onChange={(event) => setDraft({ ...draft, requireMention: event.target.checked })} type="checkbox" /> Require a Discord bot mention</label>
        </section>
      </form>
    </div>
  );
}
