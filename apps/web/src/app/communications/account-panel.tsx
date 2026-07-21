"use client";

import { useState, type FormEvent } from "react";

import type { IntegrationConnection } from "../../lib/automation-api";
import {
  createCommunicationAccount,
  deleteCommunicationAccount,
  listCommunicationAccounts,
  syncCommunicationAccount,
  testCommunicationAccount,
  updateCommunicationAccount,
  type CommunicationAccount,
  type CommunicationAccountWrite,
  type CommunicationKind,
} from "../../lib/communication-api";
import styles from "./communications.module.css";

type AccountDraft = {
  name: string;
  kind: CommunicationKind;
  enabled: boolean;
  pollIntervalSeconds: number;
  host: string;
  port: number;
  security: "plain" | "starttls" | "ssl";
  folder: string;
  username: string;
  password: string;
  smtpIntegrationId: string;
  markSeenOnRead: boolean;
  apiBaseUrl: string;
  channelIds: string;
  channelLabels: string;
  token: string;
};

function emptyDraft(kind: CommunicationKind): AccountDraft {
  return {
    name: "",
    kind,
    enabled: true,
    pollIntervalSeconds: 60,
    host: "",
    port: 993,
    security: "ssl",
    folder: "INBOX",
    username: "",
    password: "",
    smtpIntegrationId: "",
    markSeenOnRead: true,
    apiBaseUrl: "https://discord.com/api/v10",
    channelIds: "",
    channelLabels: "",
    token: "",
  };
}

function labelMapText(value: unknown): string {
  if (!value || typeof value !== "object" || Array.isArray(value)) return "";
  return Object.entries(value as Record<string, unknown>)
    .filter((entry): entry is [string, string] => typeof entry[1] === "string")
    .map(([id, label]) => `${id}=${label}`)
    .join("\n");
}

function draftFromAccount(account: CommunicationAccount): AccountDraft {
  const config = account.config;
  return {
    name: account.name,
    kind: account.kind,
    enabled: account.enabled,
    pollIntervalSeconds: account.poll_interval_seconds,
    host: typeof config.host === "string" ? config.host : "",
    port: typeof config.port === "number" ? config.port : 993,
    security:
      config.security === "plain" || config.security === "starttls" || config.security === "ssl"
        ? config.security
        : "ssl",
    folder: typeof config.folder === "string" ? config.folder : "INBOX",
    username: "",
    password: "",
    smtpIntegrationId:
      typeof config.smtp_integration_id === "string" ? config.smtp_integration_id : "",
    markSeenOnRead: config.mark_seen_on_read !== false,
    apiBaseUrl:
      typeof config.api_base_url === "string"
        ? config.api_base_url
        : "https://discord.com/api/v10",
    channelIds: Array.isArray(config.channel_ids) ? config.channel_ids.join("\n") : "",
    channelLabels: labelMapText(config.channel_labels),
    token: "",
  };
}

function lines(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function channelLabels(value: string): Record<string, string> {
  return Object.fromEntries(
    value
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const separator = line.indexOf("=");
        if (separator < 1) return [line, line];
        return [line.slice(0, separator).trim(), line.slice(separator + 1).trim()];
      })
      .filter(([id, label]) => id && label),
  );
}

function payload(draft: AccountDraft, editing: boolean): CommunicationAccountWrite {
  const credentials: Record<string, string> = {};
  let config: Record<string, unknown>;
  if (draft.kind === "imap") {
    if (draft.username) credentials.username = draft.username;
    if (draft.password) credentials.password = draft.password;
    config = {
      host: draft.host.trim(),
      port: draft.port,
      security: draft.security,
      folder: draft.folder.trim(),
      smtp_integration_id: draft.smtpIntegrationId || null,
      mark_seen_on_read: draft.markSeenOnRead,
      max_messages_per_sync: 50,
    };
  } else {
    if (draft.token) credentials.token = draft.token;
    config = {
      api_base_url: draft.apiBaseUrl.trim(),
      channel_ids: lines(draft.channelIds),
      channel_labels: channelLabels(draft.channelLabels),
      max_messages_per_sync: 50,
    };
  }
  return {
    name: draft.name.trim(),
    kind: draft.kind,
    enabled: draft.enabled,
    config,
    credentials,
    poll_interval_seconds: draft.pollIntervalSeconds,
    preserve_credentials: editing,
  };
}

export function AccountPanel({
  initialAccounts,
  integrations,
  onAccountsChange,
  onInboxChange,
  allowedKinds = ["imap", "discord"],
}: {
  initialAccounts: CommunicationAccount[];
  integrations: IntegrationConnection[];
  onAccountsChange: (accounts: CommunicationAccount[]) => void;
  onInboxChange: () => Promise<void>;
  allowedKinds?: readonly CommunicationKind[];
}) {
  const defaultKind = allowedKinds[0] ?? "imap";
  const visibleInitialAccounts = initialAccounts.filter((account) =>
    allowedKinds.includes(account.kind),
  );
  const [accounts, setAccounts] = useState(visibleInitialAccounts);
  const [selectedId, setSelectedId] = useState<string | null>(
    visibleInitialAccounts[0]?.id ?? null,
  );
  const [creating, setCreating] = useState(visibleInitialAccounts.length === 0);
  const [draft, setDraft] = useState<AccountDraft>(
    visibleInitialAccounts[0]
      ? draftFromAccount(visibleInitialAccounts[0])
      : emptyDraft(defaultKind),
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = accounts.find((account) => account.id === selectedId) ?? null;
  const smtpIntegrations = integrations.filter(
    (integration) => integration.kind === "smtp" && integration.enabled,
  );

  function choose(account: CommunicationAccount) {
    setSelectedId(account.id);
    setCreating(false);
    setDraft(draftFromAccount(account));
    setNotice(null);
    setError(null);
  }

  function beginCreate() {
    setSelectedId(null);
    setCreating(true);
    setDraft(emptyDraft(defaultKind));
    setNotice(null);
    setError(null);
  }

  async function refreshAccounts(selectId?: string) {
    const next = (await listCommunicationAccounts()).filter((account) =>
      allowedKinds.includes(account.kind),
    );
    setAccounts(next);
    onAccountsChange(next);
    const target = next.find((account) => account.id === selectId);
    if (target) choose(target);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("save");
    setNotice(null);
    setError(null);
    try {
      const body = payload(draft, !creating);
      if (!body.name) throw new Error("Account name is required.");
      const saved = creating
        ? await createCommunicationAccount(body)
        : await updateCommunicationAccount(selectedId as string, body);
      await refreshAccounts(saved.id);
      setNotice(creating ? "Account added." : "Account updated.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the account.");
    } finally {
      setBusy(null);
    }
  }

  async function runAction(action: "test" | "sync" | "delete") {
    if (!selected || busy) return;
    if (action === "delete" && !window.confirm(`Delete ${selected.name} and its history?`)) {
      return;
    }
    setBusy(action);
    setNotice(null);
    setError(null);
    try {
      if (action === "test") {
        const result = await testCommunicationAccount(selected.id);
        setNotice(result.message);
      } else if (action === "sync") {
        const result = await syncCommunicationAccount(selected.id);
        setNotice(
          `Sync complete: ${result.messages_added} new message(s), ${result.automations_enqueued} task run(s) queued.`,
        );
        await onInboxChange();
      } else {
        await deleteCommunicationAccount(selected.id);
        const next = (await listCommunicationAccounts()).filter((account) =>
          allowedKinds.includes(account.kind),
        );
        setAccounts(next);
        onAccountsChange(next);
        if (next[0]) choose(next[0]);
        else beginCreate();
        setNotice("Account deleted.");
      }
      if (action !== "delete") await refreshAccounts(selected.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not ${action} the account.`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={styles.managementLayout}>
      <aside className={styles.sideList}>
        <button className={styles.newButton} onClick={beginCreate} type="button">
          Add {defaultKind === "imap" ? "email account" : "Discord connection"}
        </button>
        {accounts.map((account) => (
          <button
            className={selectedId === account.id && !creating ? styles.selectedItem : ""}
            key={account.id}
            onClick={() => choose(account)}
            type="button"
          >
            <span className={account.enabled ? styles.enabledDot : styles.disabledDot} />
            <div>
              <strong>{account.name}</strong>
              <span>
                {account.kind} · {account.last_sync_status ?? "not tested"}
              </span>
            </div>
          </button>
        ))}
      </aside>

      <form className={styles.editor} onSubmit={(event) => void save(event)}>
        <header className={styles.editorHeader}>
          <div>
            <p>{creating ? "New connection" : "Account settings"}</p>
            <h2>{draft.name || "Untitled account"}</h2>
            <span>Credentials are encrypted and never returned by the API.</span>
          </div>
          <div className={styles.headerActions}>
            {!creating ? (
              <>
                <button disabled={Boolean(busy)} onClick={() => void runAction("test")} type="button">
                  Test
                </button>
                <button disabled={Boolean(busy)} onClick={() => void runAction("sync")} type="button">
                  Sync now
                </button>
                <button disabled={Boolean(busy)} onClick={() => void runAction("delete")} type="button">
                  Delete
                </button>
              </>
            ) : null}
            <button className={styles.primary} disabled={Boolean(busy)} type="submit">
              {busy === "save" ? "Saving…" : "Save"}
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
                maxLength={120}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                value={draft.name}
              />
            </label>
            <label>
              Type
              <select
                disabled={!creating || allowedKinds.length === 1}
                onChange={(event) => {
                  const kind = event.target.value as CommunicationKind;
                  setDraft({ ...emptyDraft(kind), name: draft.name });
                }}
                value={draft.kind}
              >
                {allowedKinds.includes("imap") ? (
                  <option value="imap">Email account · IMAP</option>
                ) : null}
                {allowedKinds.includes("discord") ? (
                  <option value="discord">Discord bot</option>
                ) : null}
              </select>
            </label>
            <label>
              Poll interval seconds
              <input
                min={10}
                onChange={(event) =>
                  setDraft({ ...draft, pollIntervalSeconds: Number(event.target.value) })
                }
                type="number"
                value={draft.pollIntervalSeconds}
              />
            </label>
            <label className={styles.check}>
              <input
                checked={draft.enabled}
                onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
                type="checkbox"
              />
              Enabled for background synchronization
            </label>
          </div>
        </section>

        {draft.kind === "imap" ? (
          <section className={styles.formSection}>
            <div className={styles.sectionTitle}>
              <p>Email</p>
              <h3>IMAP connection and mailbox discovery</h3>
            </div>
            <div className={styles.gridThree}>
              <label>
                Host
                <input
                  onChange={(event) => setDraft({ ...draft, host: event.target.value })}
                  placeholder="imap.example.com"
                  value={draft.host}
                />
              </label>
              <label>
                Port
                <input
                  min={1}
                  onChange={(event) => setDraft({ ...draft, port: Number(event.target.value) })}
                  type="number"
                  value={draft.port}
                />
              </label>
              <label>
                Security
                <select
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      security: event.target.value as AccountDraft["security"],
                    })
                  }
                  value={draft.security}
                >
                  <option value="ssl">TLS / SSL</option>
                  <option value="starttls">STARTTLS</option>
                  <option value="plain">Plain</option>
                </select>
              </label>
              <label>
                Primary mailbox fallback
                <input
                  onChange={(event) => setDraft({ ...draft, folder: event.target.value })}
                  value={draft.folder}
                />
              </label>
              <label>
                Username
                <input
                  autoComplete="username"
                  onChange={(event) => setDraft({ ...draft, username: event.target.value })}
                  placeholder={creating ? "Required" : "Leave blank to keep current"}
                  value={draft.username}
                />
              </label>
              <label>
                Password
                <input
                  autoComplete="new-password"
                  onChange={(event) => setDraft({ ...draft, password: event.target.value })}
                  placeholder={creating ? "Required" : "Leave blank to keep current"}
                  type="password"
                  value={draft.password}
                />
              </label>
              <label>
                SMTP replies
                <select
                  onChange={(event) =>
                    setDraft({ ...draft, smtpIntegrationId: event.target.value })
                  }
                  value={draft.smtpIntegrationId}
                >
                  <option value="">Read only</option>
                  {smtpIntegrations.map((integration) => (
                    <option key={integration.id} value={integration.id}>
                      {integration.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.check}>
                <input
                  checked={draft.markSeenOnRead}
                  onChange={(event) =>
                    setDraft({ ...draft, markSeenOnRead: event.target.checked })
                  }
                  type="checkbox"
                />
                Mark email as seen when read here
              </label>
            </div>
            <p className={styles.help}>
              Aster discovers every selectable IMAP mailbox during synchronization. The fallback is
              used only when the server does not expose a mailbox list.
            </p>
          </section>
        ) : (
          <section className={styles.formSection}>
            <div className={styles.sectionTitle}>
              <p>Discord</p>
              <h3>Bot and allowed channels</h3>
            </div>
            <div className={styles.gridTwo}>
              <label>
                API base URL
                <input
                  onChange={(event) => setDraft({ ...draft, apiBaseUrl: event.target.value })}
                  value={draft.apiBaseUrl}
                />
              </label>
              <label>
                Bot token
                <input
                  autoComplete="new-password"
                  onChange={(event) => setDraft({ ...draft, token: event.target.value })}
                  placeholder={creating ? "Required" : "Leave blank to keep current"}
                  type="password"
                  value={draft.token}
                />
              </label>
              <label>
                Allowed channel IDs
                <textarea
                  onChange={(event) => setDraft({ ...draft, channelIds: event.target.value })}
                  placeholder="One channel ID per line"
                  rows={6}
                  value={draft.channelIds}
                />
              </label>
              <label>
                Optional channel labels
                <textarea
                  onChange={(event) => setDraft({ ...draft, channelLabels: event.target.value })}
                  placeholder={"123456789=Support\n987654321=Operations"}
                  rows={6}
                  value={draft.channelLabels}
                />
              </label>
            </div>
            <p className={styles.help}>
              Aster reads only the explicitly allowed channels, stores searchable message history,
              can draft or send confirmed replies, and disables Discord mention parsing on every
              outbound message. It does not provide voice, calls, roles, or server administration.
            </p>
          </section>
        )}

        {!creating && selected ? (
          <section className={styles.statusGrid}>
            <div>
              <span>Last sync</span>
              <strong>
                {selected.last_sync_at
                  ? new Date(selected.last_sync_at).toLocaleString()
                  : "Never"}
              </strong>
            </div>
            <div>
              <span>Next sync</span>
              <strong>
                {selected.next_sync_at
                  ? new Date(selected.next_sync_at).toLocaleString()
                  : "Disabled"}
              </strong>
            </div>
            <div>
              <span>Stored credentials</span>
              <strong>{selected.credential_names.join(", ") || "None"}</strong>
            </div>
            <div>
              <span>Identity</span>
              <strong>
                {String(
                  selected.external_identity.username ??
                    selected.external_identity.id ??
                    "Not tested",
                )}
              </strong>
            </div>
          </section>
        ) : null}
      </form>
    </div>
  );
}
