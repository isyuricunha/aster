"use client";

import { useMemo, useState, type FormEvent } from "react";

import type { CachedModel, Persona } from "../../lib/api";
import {
  createAutomation,
  deleteAutomation,
  listAutomationRuns,
  listAutomations,
  listNotifications,
  rotateWebhookToken,
  runAutomation,
  updateAutomation,
  type Automation,
  type AutomationDeliveryWrite,
  type AutomationRun,
  type AutomationWrite,
  type IntegrationConnection,
  type NotificationList,
  type TriggerType,
} from "../../lib/automation-api";
import { Icon } from "../ui/icons";
import { AutomationHistory } from "./history-panel";
import { IntegrationPanel } from "./integration-panel";
import styles from "./automations.module.css";

type Tab = "automations" | "runs" | "integrations" | "notifications";

type DeliveryDraft = {
  integrationId: string;
  channel: "email" | "calendar" | "webhook";
  recipients: string;
  subject: string;
  summary: string;
  durationMinutes: number;
};

type AutomationDraft = {
  name: string;
  description: string;
  instruction: string;
  enabled: boolean;
  triggerType: TriggerType;
  timezone: string;
  runAt: string;
  intervalSeconds: number;
  dailyTime: string;
  weekday: number;
  modelId: string;
  personaChoice: string;
  notifyOnSuccess: boolean;
  notifyOnFailure: boolean;
  maxAttempts: number;
  retryDelaySeconds: number;
  timeoutSeconds: number;
  deliveries: DeliveryDraft[];
};

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function localDateTime(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function emptyDraft(): AutomationDraft {
  const nextHour = new Date(Date.now() + 60 * 60 * 1000);
  nextHour.setMinutes(0, 0, 0);
  return {
    name: "",
    description: "",
    instruction: "",
    enabled: true,
    triggerType: "daily",
    timezone: "UTC",
    runAt: localDateTime(nextHour.toISOString()),
    intervalSeconds: 3600,
    dailyTime: "08:00",
    weekday: 0,
    modelId: "",
    personaChoice: "none",
    notifyOnSuccess: true,
    notifyOnFailure: true,
    maxAttempts: 3,
    retryDelaySeconds: 60,
    timeoutSeconds: 300,
    deliveries: [],
  };
}

function draftFromAutomation(automation: Automation): AutomationDraft {
  const schedule = automation.schedule;
  return {
    name: automation.name,
    description: automation.description,
    instruction: automation.instruction,
    enabled: automation.enabled,
    triggerType: automation.trigger_type,
    timezone: automation.timezone,
    runAt: localDateTime(typeof schedule.run_at === "string" ? schedule.run_at : null),
    intervalSeconds:
      typeof schedule.interval_seconds === "number" ? schedule.interval_seconds : 3600,
    dailyTime: typeof schedule.time === "string" ? schedule.time : "08:00",
    weekday: typeof schedule.weekday === "number" ? schedule.weekday : 0,
    modelId: automation.model_id ?? "",
    personaChoice: automation.persona_id ?? (automation.persona_name ? "snapshot" : "none"),
    notifyOnSuccess: automation.notify_on_success,
    notifyOnFailure: automation.notify_on_failure,
    maxAttempts: automation.max_attempts,
    retryDelaySeconds: automation.retry_delay_seconds,
    timeoutSeconds: automation.timeout_seconds,
    deliveries: automation.deliveries.map((delivery) => ({
      integrationId: delivery.integration_id,
      channel: delivery.channel,
      recipients: Array.isArray(delivery.config.recipients)
        ? delivery.config.recipients.join(", ")
        : "",
      subject: typeof delivery.config.subject === "string" ? delivery.config.subject : "",
      summary: typeof delivery.config.summary === "string" ? delivery.config.summary : "",
      durationMinutes:
        typeof delivery.config.duration_minutes === "number"
          ? delivery.config.duration_minutes
          : 30,
    })),
  };
}

function schedulePayload(draft: AutomationDraft): Record<string, unknown> {
  if (draft.triggerType === "once") {
    if (!draft.runAt) throw new Error("Choose when the one-time automation should run.");
    return { run_at: new Date(draft.runAt).toISOString() };
  }
  if (draft.triggerType === "interval") {
    return { interval_seconds: draft.intervalSeconds };
  }
  if (draft.triggerType === "daily") return { time: draft.dailyTime };
  if (draft.triggerType === "weekly") {
    return { time: draft.dailyTime, weekday: draft.weekday };
  }
  return {};
}

function deliveryPayload(deliveries: DeliveryDraft[]): AutomationDeliveryWrite[] {
  return deliveries.map((delivery) => {
    let config: Record<string, unknown> = {};
    if (delivery.channel === "email") {
      config = {
        recipients: delivery.recipients
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        subject: delivery.subject.trim() || undefined,
      };
    } else if (delivery.channel === "calendar") {
      config = {
        summary: delivery.summary.trim() || undefined,
        duration_minutes: delivery.durationMinutes,
      };
    }
    return {
      integration_id: delivery.integrationId,
      channel: delivery.channel,
      enabled: true,
      config,
    };
  });
}

function payloadFromDraft(draft: AutomationDraft): AutomationWrite {
  const personaId =
    draft.personaChoice !== "none" &&
    draft.personaChoice !== "default" &&
    draft.personaChoice !== "snapshot"
      ? draft.personaChoice
      : null;
  return {
    name: draft.name.trim(),
    description: draft.description.trim(),
    instruction: draft.instruction.trim(),
    enabled: draft.enabled,
    trigger_type: draft.triggerType,
    timezone: draft.timezone.trim(),
    schedule: schedulePayload(draft),
    model_id: draft.modelId || null,
    persona_id: personaId,
    use_default_persona: draft.personaChoice === "default",
    notify_on_success: draft.notifyOnSuccess,
    notify_on_failure: draft.notifyOnFailure,
    max_attempts: draft.maxAttempts,
    retry_delay_seconds: draft.retryDelaySeconds,
    timeout_seconds: draft.timeoutSeconds,
    deliveries: deliveryPayload(draft.deliveries),
  };
}

function integrationChannel(kind: IntegrationConnection["kind"]): DeliveryDraft["channel"] {
  if (kind === "smtp") return "email";
  if (kind === "caldav") return "calendar";
  return "webhook";
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Not yet";
}

export function AutomationWorkspace({
  initialAutomations,
  initialRuns,
  initialIntegrations,
  initialNotifications,
  models,
  personas,
  initialError,
}: {
  initialAutomations: Automation[];
  initialRuns: AutomationRun[];
  initialIntegrations: IntegrationConnection[];
  initialNotifications: NotificationList;
  models: CachedModel[];
  personas: Persona[];
  initialError: string | null;
}) {
  const [tab, setTab] = useState<Tab>("automations");
  const [automations, setAutomations] = useState(initialAutomations);
  const [runs, setRuns] = useState(initialRuns);
  const [integrations, setIntegrations] = useState(initialIntegrations);
  const [notifications, setNotifications] = useState(initialNotifications);
  const [selectedId, setSelectedId] = useState<string | null>(initialAutomations[0]?.id ?? null);
  const [creating, setCreating] = useState(initialAutomations.length === 0);
  const [draft, setDraft] = useState<AutomationDraft>(
    initialAutomations[0] ? draftFromAutomation(initialAutomations[0]) : emptyDraft(),
  );
  const [webhookToken, setWebhookToken] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(initialError);
  const selected = automations.find((automation) => automation.id === selectedId) ?? null;

  const availableModels = useMemo(
    () => models.filter((model) => model.is_available),
    [models],
  );
  const enabledPersonas = useMemo(
    () => personas.filter((persona) => persona.enabled),
    [personas],
  );

  function chooseAutomation(automation: Automation) {
    setSelectedId(automation.id);
    setCreating(false);
    setDraft(draftFromAutomation(automation));
    setWebhookToken(null);
    setError(null);
  }

  function beginCreate() {
    setSelectedId(null);
    setCreating(true);
    setDraft(emptyDraft());
    setWebhookToken(null);
    setError(null);
  }

  async function refreshActivity() {
    const [nextRuns, nextNotifications] = await Promise.all([
      listAutomationRuns(),
      listNotifications(),
    ]);
    setRuns(nextRuns);
    setNotifications(nextNotifications);
  }

  async function saveAutomation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (working) return;
    setWorking(true);
    setError(null);
    try {
      const payload = payloadFromDraft(draft);
      if (!payload.name || !payload.instruction) {
        throw new Error("Name and instruction are required.");
      }
      const saved = creating
        ? await createAutomation(payload)
        : await updateAutomation(selectedId as string, payload);
      setWebhookToken(saved.webhook_token);
      setCreating(false);
      setSelectedId(saved.id);
      setDraft(draftFromAutomation(saved));
      setAutomations(await listAutomations());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the automation.");
    } finally {
      setWorking(false);
    }
  }

  async function removeAutomation() {
    if (!selected || !window.confirm(`Delete ${selected.name} and its run history?`)) return;
    setWorking(true);
    setError(null);
    try {
      await deleteAutomation(selected.id);
      const next = await listAutomations();
      setAutomations(next);
      if (next[0]) chooseAutomation(next[0]);
      else beginCreate();
      await refreshActivity();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the automation.");
    } finally {
      setWorking(false);
    }
  }

  async function runNow() {
    if (!selected || working) return;
    setWorking(true);
    setError(null);
    try {
      await runAutomation(selected.id);
      await refreshActivity();
      setTab("runs");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not queue the automation.");
    } finally {
      setWorking(false);
    }
  }

  async function rotateToken() {
    if (!selected || working) return;
    setWorking(true);
    setError(null);
    try {
      const updated = await rotateWebhookToken(selected.id);
      setWebhookToken(updated.webhook_token);
      setAutomations((current) =>
        current.map((automation) => (automation.id === updated.id ? updated : automation)),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not rotate the webhook token.");
    } finally {
      setWorking(false);
    }
  }

  function addDelivery(integrationId: string) {
    const integration = integrations.find((item) => item.id === integrationId);
    if (!integration) return;
    setDraft((current) => ({
      ...current,
      deliveries: [
        ...current.deliveries,
        {
          integrationId: integration.id,
          channel: integrationChannel(integration.kind),
          recipients: "",
          subject: "",
          summary: "",
          durationMinutes: 30,
        },
      ],
    }));
  }

  return (
    <div className={styles.workspace}>
      {error ? <div className={styles.error}>{error}</div> : null}
      <nav className={styles.tabs} aria-label="Automation sections">
        <button className={tab === "automations" ? styles.activeTab : ""} onClick={() => setTab("automations")} type="button">
          Automations <span>{automations.length}</span>
        </button>
        <button className={tab === "runs" ? styles.activeTab : ""} onClick={() => setTab("runs")} type="button">
          Runs <span>{runs.length}</span>
        </button>
        <button className={tab === "integrations" ? styles.activeTab : ""} onClick={() => setTab("integrations")} type="button">
          Integrations <span>{integrations.length}</span>
        </button>
        <button className={tab === "notifications" ? styles.activeTab : ""} onClick={() => setTab("notifications")} type="button">
          Notifications <span>{notifications.unread_count}</span>
        </button>
      </nav>

      {tab === "automations" ? (
        <div className={styles.editorLayout}>
          <aside className={styles.automationList}>
            <button className={styles.newButton} onClick={beginCreate} type="button">
              <Icon name="new-chat" size={14} /> New automation
            </button>
            {automations.map((automation) => (
              <button
                className={selectedId === automation.id && !creating ? styles.selectedAutomation : ""}
                key={automation.id}
                onClick={() => chooseAutomation(automation)}
                type="button"
              >
                <span className={automation.enabled ? styles.enabledDot : styles.disabledDot} />
                <div>
                  <strong>{automation.name}</strong>
                  <span>{automation.trigger_type} · {formatDate(automation.next_run_at)}</span>
                </div>
              </button>
            ))}
          </aside>

          <form className={styles.editor} onSubmit={(event) => void saveAutomation(event)}>
            <header className={styles.editorHeader}>
              <div>
                <p>{creating ? "New automation" : "Automation settings"}</p>
                <h2>{draft.name || "Untitled automation"}</h2>
                <span>Every run is persisted before its result is delivered.</span>
              </div>
              <div className={styles.headerActions}>
                {!creating ? <button disabled={working} onClick={() => void runNow()} type="button"><Icon name="arrow-up" size={13} /> Run now</button> : null}
                {!creating ? <button disabled={working} onClick={() => void removeAutomation()} type="button"><Icon name="trash" size={13} /> Delete</button> : null}
                <button className={styles.primary} disabled={working} type="submit">{working ? "Saving…" : "Save"}</button>
              </div>
            </header>

            <section className={styles.formSection}>
              <div className={styles.sectionTitle}><p>Definition</p><h3>What should happen?</h3></div>
              <div className={styles.gridTwo}>
                <label>Name<input maxLength={160} onChange={(event) => setDraft({ ...draft, name: event.target.value })} value={draft.name} /></label>
                <label>Description<input maxLength={500} onChange={(event) => setDraft({ ...draft, description: event.target.value })} value={draft.description} /></label>
              </div>
              <label>Instruction<textarea onChange={(event) => setDraft({ ...draft, instruction: event.target.value })} rows={7} value={draft.instruction} /></label>
              <label className={styles.check}><input checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} type="checkbox" /> Enabled and allowed to enqueue new runs</label>
            </section>

            <section className={styles.formSection}>
              <div className={styles.sectionTitle}><p>Schedule</p><h3>When should it run?</h3></div>
              <div className={styles.gridThree}>
                <label>Trigger<select onChange={(event) => setDraft({ ...draft, triggerType: event.target.value as TriggerType })} value={draft.triggerType}><option value="once">One time</option><option value="interval">Fixed interval</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="webhook">Inbound webhook</option></select></label>
                <label>Timezone<input onChange={(event) => setDraft({ ...draft, timezone: event.target.value })} placeholder="America/Sao_Paulo" value={draft.timezone} /></label>
                {draft.triggerType === "once" ? <label>Run at<input onChange={(event) => setDraft({ ...draft, runAt: event.target.value })} type="datetime-local" value={draft.runAt} /></label> : null}
                {draft.triggerType === "interval" ? <label>Every seconds<input min={60} onChange={(event) => setDraft({ ...draft, intervalSeconds: Number(event.target.value) })} type="number" value={draft.intervalSeconds} /></label> : null}
                {draft.triggerType === "daily" || draft.triggerType === "weekly" ? <label>Local time<input onChange={(event) => setDraft({ ...draft, dailyTime: event.target.value })} type="time" value={draft.dailyTime} /></label> : null}
                {draft.triggerType === "weekly" ? <label>Weekday<select onChange={(event) => setDraft({ ...draft, weekday: Number(event.target.value) })} value={draft.weekday}>{weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}</select></label> : null}
              </div>
              {draft.triggerType === "webhook" && selected?.webhook_configured ? (
                <div className={styles.secretBox}>
                  <div><strong>Inbound webhook configured</strong><span>The secret token is shown only when created or rotated.</span></div>
                  <button disabled={working} onClick={() => void rotateToken()} type="button">Rotate token</button>
                </div>
              ) : null}
              {webhookToken && selectedId ? (
                <div className={styles.tokenBox}>
                  <strong>Copy these webhook credentials now</strong>
                  <span>Endpoint</span>
                  <code>{`${window.location.origin}/api/webhooks/${selectedId}`}</code>
                  <span>Request header</span>
                  <code>{`X-Aster-Webhook-Token: ${webhookToken}`}</code>
                </div>
              ) : null}
            </section>

            <section className={styles.formSection}>
              <div className={styles.sectionTitle}><p>Context</p><h3>Which identity and model?</h3></div>
              <div className={styles.gridTwo}>
                <label>Model<select onChange={(event) => setDraft({ ...draft, modelId: event.target.value })} value={draft.modelId}><option value="">Primary with fallback chain</option>{availableModels.map((model) => <option key={model.id} value={model.id}>{model.endpoint_name} / {model.model_id}</option>)}</select></label>
                <label>Persona<select onChange={(event) => setDraft({ ...draft, personaChoice: event.target.value })} value={draft.personaChoice}><option value="none">No persona</option><option value="default">Current default persona</option>{draft.personaChoice === "snapshot" ? <option value="snapshot">Saved persona snapshot</option> : null}{enabledPersonas.map((persona) => <option key={persona.id} value={persona.id}>{persona.name}</option>)}</select></label>
              </div>
              <p className={styles.help}>Persona instructions are frozen into the automation when you save it. Model credentials never enter the prompt.</p>
            </section>

            <section className={styles.formSection}>
              <div className={styles.sectionTitle}><p>Delivery</p><h3>Where should the result go?</h3></div>
              <div className={styles.deliveryToolbar}>
                <select defaultValue="" onChange={(event) => { addDelivery(event.target.value); event.target.value = ""; }}><option value="" disabled>Add an integration…</option>{integrations.filter((item) => item.enabled).map((integration) => <option key={integration.id} value={integration.id}>{integration.name} · {integration.kind}</option>)}</select>
                <button onClick={() => setTab("integrations")} type="button">Manage integrations</button>
              </div>
              {draft.deliveries.length === 0 ? <div className={styles.emptyInline}>No external delivery. The result remains in run history and notifications.</div> : null}
              <div className={styles.deliveryList}>
                {draft.deliveries.map((delivery, index) => {
                  const integration = integrations.find((item) => item.id === delivery.integrationId);
                  return (
                    <article key={`${delivery.integrationId}-${index}`}>
                      <header><div><strong>{integration?.name ?? "Missing integration"}</strong><span>{delivery.channel}</span></div><button onClick={() => setDraft({ ...draft, deliveries: draft.deliveries.filter((_, itemIndex) => itemIndex !== index) })} type="button"><Icon name="close" size={12} /></button></header>
                      {delivery.channel === "email" ? <div className={styles.gridTwo}><label>Recipients<input onChange={(event) => setDraft({ ...draft, deliveries: draft.deliveries.map((item, itemIndex) => itemIndex === index ? { ...item, recipients: event.target.value } : item) })} placeholder="one@example.com, two@example.com" value={delivery.recipients} /></label><label>Subject<input onChange={(event) => setDraft({ ...draft, deliveries: draft.deliveries.map((item, itemIndex) => itemIndex === index ? { ...item, subject: event.target.value } : item) })} value={delivery.subject} /></label></div> : null}
                      {delivery.channel === "calendar" ? <div className={styles.gridTwo}><label>Event title<input onChange={(event) => setDraft({ ...draft, deliveries: draft.deliveries.map((item, itemIndex) => itemIndex === index ? { ...item, summary: event.target.value } : item) })} value={delivery.summary} /></label><label>Duration minutes<input min={5} onChange={(event) => setDraft({ ...draft, deliveries: draft.deliveries.map((item, itemIndex) => itemIndex === index ? { ...item, durationMinutes: Number(event.target.value) } : item) })} type="number" value={delivery.durationMinutes} /></label></div> : null}
                      {delivery.channel === "webhook" ? <p>The completed run is posted as structured JSON.</p> : null}
                    </article>
                  );
                })}
              </div>
            </section>

            <section className={styles.formSection}>
              <div className={styles.sectionTitle}><p>Reliability</p><h3>Limits, retries, and notifications</h3></div>
              <div className={styles.gridThree}>
                <label>Max attempts<input max={10} min={1} onChange={(event) => setDraft({ ...draft, maxAttempts: Number(event.target.value) })} type="number" value={draft.maxAttempts} /></label>
                <label>Retry delay seconds<input min={0} onChange={(event) => setDraft({ ...draft, retryDelaySeconds: Number(event.target.value) })} type="number" value={draft.retryDelaySeconds} /></label>
                <label>Timeout seconds<input max={3600} min={10} onChange={(event) => setDraft({ ...draft, timeoutSeconds: Number(event.target.value) })} type="number" value={draft.timeoutSeconds} /></label>
              </div>
              <div className={styles.checkRow}><label className={styles.check}><input checked={draft.notifyOnSuccess} onChange={(event) => setDraft({ ...draft, notifyOnSuccess: event.target.checked })} type="checkbox" /> Notify on success</label><label className={styles.check}><input checked={draft.notifyOnFailure} onChange={(event) => setDraft({ ...draft, notifyOnFailure: event.target.checked })} type="checkbox" /> Notify on failure</label></div>
            </section>
          </form>
        </div>
      ) : null}

      {tab === "runs" ? <AutomationHistory runs={runs} onRunsChange={setRuns} /> : null}
      {tab === "integrations" ? <IntegrationPanel integrations={integrations} onChange={setIntegrations} /> : null}
      {tab === "notifications" ? <AutomationHistory notifications={notifications} onNotificationsChange={setNotifications} /> : null}
    </div>
  );
}
