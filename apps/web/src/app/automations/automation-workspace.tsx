"use client";

import { useMemo, useState, type FormEvent } from "react";

import type { CachedModel, Persona } from "../../lib/api";
import {
  createAutomation,
  deleteAutomation,
  listAutomationRuns,
  listAutomations,
  rotateWebhookToken,
  runAutomation,
  updateAutomation,
  type Automation,
  type AutomationDeliveryWrite,
  type AutomationRun,
  type AutomationWrite,
  type IntegrationConnection,
  type TriggerType,
} from "../../lib/automation-api";
import { ModelSelect } from "../settings/models/model-browser";
import styles from "./automations.module.css";

type AutomationDraft = {
  name: string;
  description: string;
  instruction: string;
  enabled: boolean;
  triggerType: TriggerType;
  timezone: string;
  runAt: string;
  intervalSeconds: string;
  clock: string;
  weekday: string;
  modelId: string;
  personaId: string;
  notifyOnSuccess: boolean;
  notifyOnFailure: boolean;
  maxAttempts: string;
  retryDelaySeconds: string;
  timeoutSeconds: string;
  deliveries: DeliveryDraft[];
};

type DeliveryDraft = {
  integrationId: string;
  channel: "email" | "calendar" | "webhook";
  enabled: boolean;
  recipients: string;
  subject: string;
  eventTitle: string;
  durationMinutes: string;
};

const defaultDraft: AutomationDraft = {
  name: "",
  description: "",
  instruction: "",
  enabled: true,
  triggerType: "daily",
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  runAt: "",
  intervalSeconds: "3600",
  clock: "09:00",
  weekday: "0",
  modelId: "",
  personaId: "",
  notifyOnSuccess: true,
  notifyOnFailure: true,
  maxAttempts: "3",
  retryDelaySeconds: "60",
  timeoutSeconds: "300",
  deliveries: [],
};

function toLocalInput(value: unknown): string {
  if (typeof value !== "string") return "";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "";
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.valueOf() - offset).toISOString().slice(0, 16);
}

function deliveryDraft(delivery: Automation["deliveries"][number]): DeliveryDraft {
  return {
    integrationId: delivery.integration_id,
    channel: delivery.channel,
    enabled: delivery.enabled,
    recipients: Array.isArray(delivery.config.recipients)
      ? delivery.config.recipients.join(", ")
      : "",
    subject: typeof delivery.config.subject === "string" ? delivery.config.subject : "",
    eventTitle:
      typeof delivery.config.event_title === "string" ? delivery.config.event_title : "",
    durationMinutes:
      typeof delivery.config.duration_minutes === "number"
        ? String(delivery.config.duration_minutes)
        : "60",
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
    runAt: toLocalInput(schedule.run_at),
    intervalSeconds:
      typeof schedule.interval_seconds === "number" ? String(schedule.interval_seconds) : "3600",
    clock: typeof schedule.time === "string" ? schedule.time : "09:00",
    weekday: typeof schedule.weekday === "number" ? String(schedule.weekday) : "0",
    modelId: automation.model_id ?? "",
    personaId: automation.persona_id ?? "",
    notifyOnSuccess: automation.notify_on_success,
    notifyOnFailure: automation.notify_on_failure,
    maxAttempts: String(automation.max_attempts),
    retryDelaySeconds: String(automation.retry_delay_seconds),
    timeoutSeconds: String(automation.timeout_seconds),
    deliveries: automation.deliveries.map(deliveryDraft),
  };
}

function schedulePayload(draft: AutomationDraft): Record<string, object> {
  if (draft.triggerType === "once") {
    return { run_at: new Date(draft.runAt).toISOString() };
  }
  if (draft.triggerType === "interval") {
    return { interval_seconds: Number(draft.intervalSeconds) };
  }
  if (draft.triggerType === "daily") {
    return { time: draft.clock };
  }
  if (draft.triggerType === "weekly") {
    return { time: draft.clock, weekday: Number(draft.weekday) };
  }
  return {};
}

function deliveryPayload(delivery: DeliveryDraft): AutomationDeliveryWrite {
  const config: Record<string, object> = {};
  if (delivery.channel === "email") {
    config.recipients = delivery.recipients
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    if (delivery.subject.trim()) config.subject = delivery.subject.trim();
  }
  if (delivery.channel === "calendar") {
    config.event_title = delivery.eventTitle.trim();
    config.duration_minutes = Number(delivery.durationMinutes);
  }
  return {
    integration_id: delivery.integrationId,
    channel: delivery.channel,
    enabled: delivery.enabled,
    config,
  };
}

function automationPayload(draft: AutomationDraft): AutomationWrite {
  return {
    name: draft.name,
    description: draft.description,
    instruction: draft.instruction,
    enabled: draft.enabled,
    trigger_type: draft.triggerType,
    timezone: draft.timezone,
    schedule: schedulePayload(draft),
    model_id: draft.modelId || null,
    persona_id: draft.personaId || null,
    use_default_persona: false,
    notify_on_success: draft.notifyOnSuccess,
    notify_on_failure: draft.notifyOnFailure,
    max_attempts: Number(draft.maxAttempts),
    retry_delay_seconds: Number(draft.retryDelaySeconds),
    timeout_seconds: Number(draft.timeoutSeconds),
    deliveries: draft.deliveries.map(deliveryPayload),
  };
}

function formatDate(value: string | null): string {
  if (!value) return "Not scheduled";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AutomationWorkspace({
  initialAutomations,
  initialRuns,
  models,
  personas,
  integrations,
}: {
  initialAutomations: Automation[];
  initialRuns: AutomationRun[];
  models: CachedModel[];
  personas: Persona[];
  integrations: IntegrationConnection[];
}) {
  const [automations, setAutomations] = useState(initialAutomations);
  const [runs, setRuns] = useState(initialRuns);
  const [selectedId, setSelectedId] = useState<string | null>(initialAutomations[0]?.id ?? null);
  const [draft, setDraft] = useState<AutomationDraft>(
    initialAutomations[0] ? draftFromAutomation(initialAutomations[0]) : defaultDraft,
  );
  const [creating, setCreating] = useState(initialAutomations.length === 0);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = automations.find((item) => item.id === selectedId) ?? null;

  const selectableModels = useMemo(
    () => models.filter((model) => model.is_available),
    [models],
  );

  function choose(item: Automation) {
    setSelectedId(item.id);
    setDraft(draftFromAutomation(item));
    setCreating(false);
    setNotice(null);
    setError(null);
  }

  function beginCreate() {
    setSelectedId(null);
    setDraft(defaultDraft);
    setCreating(true);
    setNotice(null);
    setError(null);
  }

  async function refresh(selectId?: string) {
    const [nextAutomations, nextRuns] = await Promise.all([
      listAutomations(),
      listAutomationRuns(),
    ]);
    setAutomations(nextAutomations);
    setRuns(nextRuns);
    const target = nextAutomations.find((item) => item.id === selectId);
    if (target) choose(target);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("save");
    setNotice(null);
    setError(null);
    try {
      const payload = automationPayload(draft);
      const saved = creating
        ? await createAutomation(payload)
        : await updateAutomation(selectedId as string, payload);
      await refresh(saved.id);
      setNotice(creating ? "Automation created." : "Automation updated.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The automation could not be saved.");
    } finally {
      setBusy(null);
    }
  }

  async function action(name: "run" | "delete" | "rotate") {
    if (!selected || busy) return;
    if (name === "delete" && !window.confirm(`Delete ${selected.name} and its complete run history?`)) {
      return;
    }
    setBusy(name);
    setNotice(null);
    setError(null);
    try {
      if (name === "run") {
        await runAutomation(selected.id);
        setNotice("Run queued.");
      } else if (name === "rotate") {
        const rotated = await rotateWebhookToken(selected.id);
        await refresh(rotated.id);
        setNotice(
          rotated.webhook_token
            ? `New webhook token: ${rotated.webhook_token}`
            : "Webhook token rotated.",
        );
      } else {
        await deleteAutomation(selected.id);
        const next = await listAutomations();
        setAutomations(next);
        setRuns(await listAutomationRuns());
        if (next[0]) choose(next[0]);
        else beginCreate();
        setNotice("Automation deleted.");
      }
      if (name !== "delete") await refresh(selected.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `The ${name} action failed.`);
    } finally {
      setBusy(null);
    }
  }

  function addDelivery() {
    const first = integrations.find((item) => item.enabled);
    if (!first) {
      setError("Add and enable an integration before adding a delivery.");
      return;
    }
    const channel = first.kind === "smtp" ? "email" : first.kind === "caldav" ? "calendar" : "webhook";
    setDraft({
      ...draft,
      deliveries: [
        ...draft.deliveries,
        {
          integrationId: first.id,
          channel,
          enabled: true,
          recipients: "",
          subject: "",
          eventTitle: "",
          durationMinutes: "60",
        },
      ],
    });
  }

  function updateDelivery(index: number, values: Partial<DeliveryDraft>) {
    setDraft({
      ...draft,
      deliveries: draft.deliveries.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...values } : item,
      ),
    });
  }

  function changeDeliveryIntegration(index: number, integrationId: string) {
    const integration = integrations.find((item) => item.id === integrationId);
    if (!integration) return;
    const channel = integration.kind === "smtp" ? "email" : integration.kind === "caldav" ? "calendar" : "webhook";
    updateDelivery(index, { integrationId, channel });
  }

  return (
    <div className={styles.workspace}>
      <aside className={styles.automationList}>
        <button className={styles.newButton} onClick={beginCreate} type="button">
          New automation
        </button>
        {automations.map((automation) => (
          <button
            className={selectedId === automation.id && !creating ? styles.selectedAutomation : ""}
            key={automation.id}
            onClick={() => choose(automation)}
            type="button"
          >
            <span className={automation.enabled ? styles.enabledDot : styles.disabledDot} />
            <div>
              <strong>{automation.name}</strong>
              <span>
                {automation.trigger_type} · {formatDate(automation.next_run_at)}
              </span>
            </div>
          </button>
        ))}
      </aside>

      <form className={styles.editor} onSubmit={(event) => void save(event)}>
        <header className={styles.editorHeader}>
          <div>
            <p>{creating ? "New automation" : "Automation editor"}</p>
            <h2>{draft.name || "Untitled automation"}</h2>
            <span>Scheduled model output with explicit, auditable delivery.</span>
          </div>
          <div className={styles.headerActions}>
            {!creating ? (
              <>
                <button disabled={Boolean(busy)} onClick={() => void action("run")} type="button">
                  Run now
                </button>
                {selected?.trigger_type === "webhook" ? (
                  <button disabled={Boolean(busy)} onClick={() => void action("rotate")} type="button">
                    Rotate token
                  </button>
                ) : null}
                <button disabled={Boolean(busy)} onClick={() => void action("delete")} type="button">
                  Delete
                </button>
              </>
            ) : null}
            <button className={styles.primaryButton} disabled={Boolean(busy)} type="submit">
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
                maxLength={160}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                value={draft.name}
              />
            </label>
            <label className={styles.checkLabel}>
              <input
                checked={draft.enabled}
                onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
                type="checkbox"
              />
              Enabled
            </label>
            <label className={styles.formSpanTwo}>
              Description
              <input
                maxLength={500}
                onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                value={draft.description}
              />
            </label>
            <label className={styles.formSpanTwo}>
              Instruction
              <textarea
                onChange={(event) => setDraft({ ...draft, instruction: event.target.value })}
                rows={7}
                value={draft.instruction}
              />
            </label>
          </div>
        </section>

        <section className={styles.formSection}>
          <div className={styles.sectionTitle}>
            <p>Trigger</p>
            <h3>When should it run?</h3>
          </div>
          <div className={styles.gridThree}>
            <label>
              Trigger type
              <select
                onChange={(event) =>
                  setDraft({ ...draft, triggerType: event.target.value as TriggerType })
                }
                value={draft.triggerType}
              >
                <option value="once">One time</option>
                <option value="interval">Fixed interval</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="webhook">Inbound webhook</option>
                <option value="communication">Communication message</option>
              </select>
            </label>
            <label>
              Timezone
              <input
                onChange={(event) => setDraft({ ...draft, timezone: event.target.value })}
                placeholder="America/Sao_Paulo"
                value={draft.timezone}
              />
            </label>
            {draft.triggerType === "once" ? (
              <label>
                Run at
                <input
                  onChange={(event) => setDraft({ ...draft, runAt: event.target.value })}
                  required
                  type="datetime-local"
                  value={draft.runAt}
                />
              </label>
            ) : null}
            {draft.triggerType === "interval" ? (
              <label>
                Interval seconds
                <input
                  min={60}
                  onChange={(event) =>
                    setDraft({ ...draft, intervalSeconds: event.target.value })
                  }
                  type="number"
                  value={draft.intervalSeconds}
                />
              </label>
            ) : null}
            {draft.triggerType === "daily" || draft.triggerType === "weekly" ? (
              <label>
                Local time
                <input
                  onChange={(event) => setDraft({ ...draft, clock: event.target.value })}
                  type="time"
                  value={draft.clock}
                />
              </label>
            ) : null}
            {draft.triggerType === "weekly" ? (
              <label>
                Weekday
                <select
                  onChange={(event) => setDraft({ ...draft, weekday: event.target.value })}
                  value={draft.weekday}
                >
                  <option value="0">Monday</option>
                  <option value="1">Tuesday</option>
                  <option value="2">Wednesday</option>
                  <option value="3">Thursday</option>
                  <option value="4">Friday</option>
                  <option value="5">Saturday</option>
                  <option value="6">Sunday</option>
                </select>
              </label>
            ) : null}
          </div>
          {draft.triggerType === "webhook" && selected?.webhook_path ? (
            <div className={styles.webhookCard}>
              <code>{selected.webhook_path}</code>
              <span>
                Send the secret in <code>X-Aster-Webhook-Token</code>. It is shown only after creation
                or rotation.
              </span>
            </div>
          ) : null}
          {draft.triggerType === "communication" ? (
            <div className={styles.webhookCard}>
              <span>
                Add an allowlist rule in Communications after saving. Receiving a message alone does
                not queue this automation.
              </span>
            </div>
          ) : null}
        </section>

        <section className={styles.formSection}>
          <div className={styles.sectionTitle}>
            <p>Execution</p>
            <h3>Model, persona, and bounds</h3>
          </div>
          <div className={styles.gridThree}>
            <ModelSelect
              label="Model"
              emptyLabel="Use Primary and fallbacks"
              models={selectableModels}
              onChange={(value) => setDraft({ ...draft, modelId: value })}
              value={draft.modelId}
            />
            <label>
              Persona
              <select
                onChange={(event) => setDraft({ ...draft, personaId: event.target.value })}
                value={draft.personaId}
              >
                <option value="">No persona</option>
                {personas.filter((persona) => persona.enabled).map((persona) => (
                  <option key={persona.id} value={persona.id}>
                    {persona.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Timeout seconds
              <input
                min={10}
                onChange={(event) => setDraft({ ...draft, timeoutSeconds: event.target.value })}
                type="number"
                value={draft.timeoutSeconds}
              />
            </label>
            <label>
              Maximum attempts
              <input
                max={10}
                min={1}
                onChange={(event) => setDraft({ ...draft, maxAttempts: event.target.value })}
                type="number"
                value={draft.maxAttempts}
              />
            </label>
            <label>
              Retry delay seconds
              <input
                min={0}
                onChange={(event) => setDraft({ ...draft, retryDelaySeconds: event.target.value })}
                type="number"
                value={draft.retryDelaySeconds}
              />
            </label>
            <label className={styles.checkLabel}>
              <input
                checked={draft.notifyOnSuccess}
                onChange={(event) =>
                  setDraft({ ...draft, notifyOnSuccess: event.target.checked })
                }
                type="checkbox"
              />
              Notify on success
            </label>
            <label className={styles.checkLabel}>
              <input
                checked={draft.notifyOnFailure}
                onChange={(event) =>
                  setDraft({ ...draft, notifyOnFailure: event.target.checked })
                }
                type="checkbox"
              />
              Notify on failure
            </label>
          </div>
        </section>

        <section className={styles.formSection}>
          <div className={styles.sectionTitleRow}>
            <div className={styles.sectionTitle}>
              <p>Delivery</p>
              <h3>External side effects</h3>
            </div>
            <button onClick={addDelivery} type="button">
              Add delivery
            </button>
          </div>
          {draft.deliveries.length === 0 ? (
            <div className={styles.emptyDelivery}>
              The result stays in private run history unless a delivery is added.
            </div>
          ) : (
            <div className={styles.deliveryList}>
              {draft.deliveries.map((delivery, index) => (
                <div className={styles.deliveryCard} key={`${delivery.integrationId}-${index}`}>
                  <label>
                    Integration
                    <select
                      onChange={(event) => changeDeliveryIntegration(index, event.target.value)}
                      value={delivery.integrationId}
                    >
                      {integrations.filter((item) => item.enabled).map((integration) => (
                        <option key={integration.id} value={integration.id}>
                          {integration.name} · {integration.kind}
                        </option>
                      ))}
                    </select>
                  </label>
                  {delivery.channel === "email" ? (
                    <>
                      <label>
                        Recipients
                        <input
                          onChange={(event) =>
                            updateDelivery(index, { recipients: event.target.value })
                          }
                          placeholder="one@example.com, two@example.com"
                          value={delivery.recipients}
                        />
                      </label>
                      <label>
                        Subject
                        <input
                          onChange={(event) =>
                            updateDelivery(index, { subject: event.target.value })
                          }
                          placeholder="Automation completed"
                          value={delivery.subject}
                        />
                      </label>
                    </>
                  ) : null}
                  {delivery.channel === "calendar" ? (
                    <>
                      <label>
                        Event title
                        <input
                          onChange={(event) =>
                            updateDelivery(index, { eventTitle: event.target.value })
                          }
                          value={delivery.eventTitle}
                        />
                      </label>
                      <label>
                        Duration minutes
                        <input
                          min={5}
                          onChange={(event) =>
                            updateDelivery(index, { durationMinutes: event.target.value })
                          }
                          type="number"
                          value={delivery.durationMinutes}
                        />
                      </label>
                    </>
                  ) : null}
                  <button
                    onClick={() =>
                      setDraft({
                        ...draft,
                        deliveries: draft.deliveries.filter((_, itemIndex) => itemIndex !== index),
                      })
                    }
                    type="button"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {!creating && selected ? (
          <section className={styles.runSection}>
            <div className={styles.sectionTitle}>
              <p>Recent history</p>
              <h3>Runs for this automation</h3>
            </div>
            <div className={styles.runList}>
              {runs.filter((run) => run.automation_id === selected.id).slice(0, 8).map((run) => (
                <article key={run.id}>
                  <div>
                    <strong>{run.status}</strong>
                    <span>{formatDate(run.created_at)}</span>
                  </div>
                  <p>{run.response || run.error_message || "No output yet."}</p>
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </form>
    </div>
  );
}
