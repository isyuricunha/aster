"use client";

import { useState, type FormEvent } from "react";

import {
  createIntegration,
  deleteIntegration,
  listIntegrations,
  testIntegration,
  updateIntegration,
  type IntegrationConnection,
  type IntegrationKind,
  type IntegrationWrite,
} from "../../lib/automation-api";
import { Icon } from "../ui/icons";
import styles from "./automations.module.css";

type Draft = {
  name: string;
  kind: IntegrationKind;
  enabled: boolean;
  host: string;
  port: number;
  security: "plain" | "starttls" | "ssl";
  fromAddress: string;
  url: string;
  authType: "none" | "basic" | "bearer";
  username: string;
  password: string;
  token: string;
  headers: string;
};

function blankDraft(): Draft {
  return {
    name: "",
    kind: "smtp",
    enabled: true,
    host: "",
    port: 587,
    security: "starttls",
    fromAddress: "",
    url: "",
    authType: "none",
    username: "",
    password: "",
    token: "",
    headers: "{}",
  };
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function draftFromIntegration(integration: IntegrationConnection): Draft {
  return {
    ...blankDraft(),
    name: integration.name,
    kind: integration.kind,
    enabled: integration.enabled,
    host: stringValue(integration.config.host),
    port: typeof integration.config.port === "number" ? integration.config.port : 587,
    security:
      integration.config.security === "plain" ||
      integration.config.security === "ssl" ||
      integration.config.security === "starttls"
        ? integration.config.security
        : "starttls",
    fromAddress: stringValue(integration.config.from_address),
    url: stringValue(integration.config.calendar_url ?? integration.config.url),
    authType:
      integration.config.auth_type === "basic" || integration.config.auth_type === "bearer"
        ? integration.config.auth_type
        : "none",
  };
}

function payload(draft: Draft, preserveCredentials: boolean): IntegrationWrite {
  const extra = JSON.parse(draft.headers || "{}") as unknown;
  if (!extra || Array.isArray(extra) || typeof extra !== "object") {
    throw new Error("Secret headers must be a JSON object.");
  }
  const credentials: Record<string, string> = {};
  if (draft.username) credentials.username = draft.username;
  if (draft.password) credentials.password = draft.password;
  if (draft.token) credentials.token = draft.token;
  for (const [key, value] of Object.entries(extra)) {
    if (typeof value !== "string") throw new Error("Every secret header value must be text.");
    credentials[key] = value;
  }
  let config: Record<string, unknown>;
  if (draft.kind === "smtp") {
    config = {
      host: draft.host.trim(),
      port: draft.port,
      security: draft.security,
      from_address: draft.fromAddress.trim(),
    };
  } else if (draft.kind === "caldav") {
    config = { calendar_url: draft.url.trim(), auth_type: draft.authType };
  } else {
    config = { url: draft.url.trim(), auth_type: draft.authType };
  }
  return {
    name: draft.name.trim(),
    kind: draft.kind,
    enabled: draft.enabled,
    config,
    credentials,
    preserve_credentials: preserveCredentials,
  };
}

export function IntegrationPanel({
  integrations,
  onChange,
}: {
  integrations: IntegrationConnection[];
  onChange: (items: IntegrationConnection[]) => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(integrations[0]?.id ?? null);
  const [creating, setCreating] = useState(integrations.length === 0);
  const [draft, setDraft] = useState<Draft>(
    integrations[0] ? draftFromIntegration(integrations[0]) : blankDraft(),
  );
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = integrations.find((item) => item.id === selectedId) ?? null;

  function choose(item: IntegrationConnection) {
    setSelectedId(item.id);
    setCreating(false);
    setDraft(draftFromIntegration(item));
    setMessage(null);
    setError(null);
  }

  function createNew() {
    setSelectedId(null);
    setCreating(true);
    setDraft(blankDraft());
    setMessage(null);
    setError(null);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (working) return;
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      const saved = creating
        ? await createIntegration(payload(draft, false))
        : await updateIntegration(selectedId as string, payload(draft, true));
      const next = await listIntegrations();
      onChange(next);
      setSelectedId(saved.id);
      setCreating(false);
      setDraft(draftFromIntegration(saved));
      setMessage("Integration saved. Credentials remain encrypted and are never returned.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the integration.");
    } finally {
      setWorking(false);
    }
  }

  async function test() {
    if (!selected || working) return;
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      const result = await testIntegration(selected.id);
      onChange(await listIntegrations());
      setMessage(result.message);
    } catch (caught) {
      onChange(await listIntegrations());
      setError(caught instanceof Error ? caught.message : "Integration test failed.");
    } finally {
      setWorking(false);
    }
  }

  async function remove() {
    if (!selected || !window.confirm(`Delete ${selected.name}?`)) return;
    setWorking(true);
    setError(null);
    try {
      await deleteIntegration(selected.id);
      const next = await listIntegrations();
      onChange(next);
      if (next[0]) choose(next[0]);
      else createNew();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the integration.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className={styles.editorLayout}>
      <aside className={styles.automationList}>
        <button className={styles.newButton} onClick={createNew} type="button"><Icon name="new-chat" size={14} /> New integration</button>
        {integrations.map((integration) => <button className={selectedId === integration.id && !creating ? styles.selectedAutomation : ""} key={integration.id} onClick={() => choose(integration)} type="button"><span className={integration.enabled ? styles.enabledDot : styles.disabledDot} /><div><strong>{integration.name}</strong><span>{integration.kind} · {integration.last_test_status ?? "not tested"}</span></div></button>)}
      </aside>
      <form className={styles.editor} onSubmit={(event) => void save(event)}>
        {error ? <div className={styles.error}>{error}</div> : null}
        {message ? <div className={styles.success}>{message}</div> : null}
        <header className={styles.editorHeader}><div><p>{creating ? "New connection" : "Integration settings"}</p><h2>{draft.name || "Untitled integration"}</h2><span>Credentials are encrypted and only their field names remain visible.</span></div><div className={styles.headerActions}>{!creating ? <button disabled={working} onClick={() => void test()} type="button"><Icon name="refresh" size={13} /> Test</button> : null}{!creating ? <button disabled={working} onClick={() => void remove()} type="button"><Icon name="trash" size={13} /> Delete</button> : null}<button className={styles.primary} disabled={working} type="submit">{working ? "Saving…" : "Save"}</button></div></header>
        <section className={styles.formSection}><div className={styles.gridThree}><label>Name<input onChange={(event) => setDraft({ ...draft, name: event.target.value })} value={draft.name} /></label><label>Kind<select disabled={!creating} onChange={(event) => setDraft({ ...blankDraft(), name: draft.name, kind: event.target.value as IntegrationKind })} value={draft.kind}><option value="smtp">SMTP email</option><option value="caldav">CalDAV calendar</option><option value="webhook">Outbound webhook</option></select></label><label className={styles.check}><input checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} type="checkbox" /> Enabled</label></div></section>
        {draft.kind === "smtp" ? <section className={styles.formSection}><div className={styles.sectionTitle}><p>Email</p><h3>SMTP delivery</h3></div><div className={styles.gridThree}><label>Host<input onChange={(event) => setDraft({ ...draft, host: event.target.value })} value={draft.host} /></label><label>Port<input min={1} max={65535} onChange={(event) => setDraft({ ...draft, port: Number(event.target.value) })} type="number" value={draft.port} /></label><label>Security<select onChange={(event) => setDraft({ ...draft, security: event.target.value as Draft["security"] })} value={draft.security}><option value="starttls">STARTTLS</option><option value="ssl">TLS/SSL</option><option value="plain">Plain</option></select></label></div><label>From address<input onChange={(event) => setDraft({ ...draft, fromAddress: event.target.value })} type="email" value={draft.fromAddress} /></label></section> : null}
        {draft.kind !== "smtp" ? <section className={styles.formSection}><div className={styles.sectionTitle}><p>{draft.kind === "caldav" ? "Calendar" : "Webhook"}</p><h3>{draft.kind === "caldav" ? "CalDAV collection" : "HTTP endpoint"}</h3></div><label>{draft.kind === "caldav" ? "Calendar URL" : "Webhook URL"}<input onChange={(event) => setDraft({ ...draft, url: event.target.value })} type="url" value={draft.url} /></label><label>Authentication<select onChange={(event) => setDraft({ ...draft, authType: event.target.value as Draft["authType"] })} value={draft.authType}><option value="none">None or custom headers</option><option value="basic">Basic</option><option value="bearer">Bearer token</option></select></label></section> : null}
        <section className={styles.formSection}><div className={styles.sectionTitle}><p>Secrets</p><h3>Credentials and private headers</h3></div>{selected?.credential_names.length ? <p className={styles.help}>Stored fields: {selected.credential_names.join(", ")}. Leave these blank to preserve them.</p> : null}<div className={styles.gridTwo}>{draft.kind === "smtp" || draft.authType === "basic" ? <label>Username<input autoComplete="off" onChange={(event) => setDraft({ ...draft, username: event.target.value })} value={draft.username} /></label> : null}{draft.kind === "smtp" || draft.authType === "basic" ? <label>Password<input autoComplete="new-password" onChange={(event) => setDraft({ ...draft, password: event.target.value })} type="password" value={draft.password} /></label> : null}{draft.authType === "bearer" ? <label>Bearer token<input autoComplete="off" onChange={(event) => setDraft({ ...draft, token: event.target.value })} type="password" value={draft.token} /></label> : null}</div><label>Additional secret HTTP headers<textarea onChange={(event) => setDraft({ ...draft, headers: event.target.value })} placeholder={'{"Authorization":"Bearer ...","X-Signature":"..."}'} rows={5} value={draft.headers} /></label></section>
      </form>
    </div>
  );
}
