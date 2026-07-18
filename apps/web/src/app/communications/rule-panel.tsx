"use client";

import { useMemo, useState, type FormEvent } from "react";

import type { Automation } from "../../lib/automation-api";
import {
  createCommunicationRule,
  deleteCommunicationRule,
  listCommunicationRules,
  updateCommunicationRule,
  type CommunicationAccount,
  type CommunicationRule,
  type CommunicationRuleWrite,
} from "../../lib/communication-api";
import styles from "./communications.module.css";

type RuleDraft = {
  name: string;
  accountId: string;
  automationId: string;
  enabled: boolean;
  senderPattern: string;
  sourceIds: string;
  bodyContains: string;
  requireMention: boolean;
};

function emptyDraft(accounts: CommunicationAccount[], automations: Automation[]): RuleDraft {
  return {
    name: "",
    accountId: accounts[0]?.id ?? "",
    automationId: automations[0]?.id ?? "",
    enabled: true,
    senderPattern: "",
    sourceIds: "",
    bodyContains: "",
    requireMention: false,
  };
}

function draftFromRule(rule: CommunicationRule): RuleDraft {
  return {
    name: rule.name,
    accountId: rule.account_id,
    automationId: rule.automation_id,
    enabled: rule.enabled,
    senderPattern: rule.sender_pattern ?? "",
    sourceIds: rule.source_ids.join("\n"),
    bodyContains: rule.body_contains ?? "",
    requireMention: rule.require_mention,
  };
}

function payload(draft: RuleDraft): CommunicationRuleWrite {
  return {
    name: draft.name.trim(),
    account_id: draft.accountId,
    automation_id: draft.automationId,
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
  initialRules,
  accounts,
  automations,
  onRulesChange,
}: {
  initialRules: CommunicationRule[];
  accounts: CommunicationAccount[];
  automations: Automation[];
  onRulesChange: (rules: CommunicationRule[]) => void;
}) {
  const communicationAutomations = useMemo(
    () => automations.filter((automation) => automation.trigger_type === "communication"),
    [automations],
  );
  const [rules, setRules] = useState(initialRules);
  const [selectedId, setSelectedId] = useState<string | null>(initialRules[0]?.id ?? null);
  const [creating, setCreating] = useState(initialRules.length === 0);
  const [draft, setDraft] = useState<RuleDraft>(
    initialRules[0]
      ? draftFromRule(initialRules[0])
      : emptyDraft(accounts, communicationAutomations),
  );
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = rules.find((rule) => rule.id === selectedId) ?? null;
  const selectedAccount = accounts.find((account) => account.id === draft.accountId) ?? null;

  function choose(rule: CommunicationRule) {
    setSelectedId(rule.id);
    setCreating(false);
    setDraft(draftFromRule(rule));
    setNotice(null);
    setError(null);
  }

  function beginCreate() {
    setSelectedId(null);
    setCreating(true);
    setDraft(emptyDraft(accounts, communicationAutomations));
    setNotice(null);
    setError(null);
  }

  async function refresh(selectId?: string) {
    const next = await listCommunicationRules();
    setRules(next);
    onRulesChange(next);
    const target = next.find((rule) => rule.id === selectId);
    if (target) choose(target);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      const body = payload(draft);
      if (!body.name || !body.account_id || !body.automation_id) {
        throw new Error("Name, account, and automation are required.");
      }
      const saved = creating
        ? await createCommunicationRule(body)
        : await updateCommunicationRule(selectedId as string, body);
      await refresh(saved.id);
      setNotice(creating ? "Rule created." : "Rule updated.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the rule.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!selected || busy || !window.confirm(`Delete ${selected.name}?`)) return;
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      await deleteCommunicationRule(selected.id);
      const next = await listCommunicationRules();
      setRules(next);
      onRulesChange(next);
      if (next[0]) choose(next[0]);
      else beginCreate();
      setNotice("Rule deleted.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the rule.");
    } finally {
      setBusy(false);
    }
  }

  if (accounts.length === 0) {
    return (
      <div className={styles.emptyState}>
        Add an IMAP or Discord account before creating communication rules.
      </div>
    );
  }

  if (communicationAutomations.length === 0) {
    return (
      <div className={styles.emptyState}>
        <strong>No communication automation exists yet.</strong>
        <span>
          Create an automation with the Communication message trigger, then return here to define
          which senders and channels may enqueue it.
        </span>
      </div>
    );
  }

  return (
    <div className={styles.managementLayout}>
      <aside className={styles.sideList}>
        <button className={styles.newButton} onClick={beginCreate} type="button">
          Add rule
        </button>
        {rules.map((rule) => (
          <button
            className={selectedId === rule.id && !creating ? styles.selectedItem : ""}
            key={rule.id}
            onClick={() => choose(rule)}
            type="button"
          >
            <span className={rule.enabled ? styles.enabledDot : styles.disabledDot} />
            <div>
              <strong>{rule.name}</strong>
              <span>{rule.account_name} → {rule.automation_name}</span>
            </div>
          </button>
        ))}
      </aside>

      <form className={styles.editor} onSubmit={(event) => void save(event)}>
        <header className={styles.editorHeader}>
          <div>
            <p>{creating ? "New routing rule" : "Rule settings"}</p>
            <h2>{draft.name || "Untitled rule"}</h2>
            <span>All configured conditions must match before a run is queued.</span>
          </div>
          <div className={styles.headerActions}>
            {!creating ? (
              <button disabled={busy} onClick={() => void remove()} type="button">
                Delete
              </button>
            ) : null}
            <button className={styles.primary} disabled={busy} type="submit">
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </header>

        {notice ? <div className={styles.notice}>{notice}</div> : null}
        {error ? <div className={styles.error}>{error}</div> : null}

        <section className={styles.formSection}>
          <div className={styles.gridTwo}>
            <label>
              Name
              <input
                maxLength={160}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                value={draft.name}
              />
            </label>
            <label className={styles.check}>
              <input
                checked={draft.enabled}
                onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
                type="checkbox"
              />
              Enabled
            </label>
            <label>
              Account
              <select
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    accountId: event.target.value,
                    requireMention:
                      accounts.find((account) => account.id === event.target.value)?.kind ===
                      "discord"
                        ? draft.requireMention
                        : false,
                  })
                }
                value={draft.accountId}
              >
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name} · {account.kind}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Automation
              <select
                onChange={(event) => setDraft({ ...draft, automationId: event.target.value })}
                value={draft.automationId}
              >
                {communicationAutomations.map((automation) => (
                  <option key={automation.id} value={automation.id}>
                    {automation.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </section>

        <section className={styles.formSection}>
          <div className={styles.sectionTitle}>
            <p>Allowlist</p>
            <h3>Which messages may trigger it?</h3>
          </div>
          <div className={styles.gridTwo}>
            <label>
              Sender pattern
              <input
                onChange={(event) => setDraft({ ...draft, senderPattern: event.target.value })}
                placeholder={selectedAccount?.kind === "imap" ? "*@example.com" : "Discord user ID"}
                value={draft.senderPattern}
              />
            </label>
            <label>
              Body contains
              <input
                onChange={(event) => setDraft({ ...draft, bodyContains: event.target.value })}
                placeholder="Optional case-insensitive text"
                value={draft.bodyContains}
              />
            </label>
            <label className={styles.formSpanTwo}>
              Source IDs
              <textarea
                onChange={(event) => setDraft({ ...draft, sourceIds: event.target.value })}
                placeholder={
                  selectedAccount?.kind === "discord"
                    ? "Allowed channel IDs or user IDs, one per line"
                    : "Allowed folder names or sender addresses, one per line"
                }
                rows={5}
                value={draft.sourceIds}
              />
            </label>
          </div>
          {selectedAccount?.kind === "discord" ? (
            <label className={styles.check}>
              <input
                checked={draft.requireMention}
                onChange={(event) =>
                  setDraft({ ...draft, requireMention: event.target.checked })
                }
                type="checkbox"
              />
              Require the bot to be mentioned
            </label>
          ) : null}
          <p className={styles.help}>
            A matching rule only queues the selected automation. It does not send a reply or grant
            the model access to the communication account.
          </p>
        </section>
      </form>
    </div>
  );
}
