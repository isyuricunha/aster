"use client";

import { useRef, useState, type KeyboardEvent } from "react";

import type { CachedModel, Persona } from "../../lib/api";
import {
  cancelAutomationRun,
  deleteNotification,
  listAutomationRuns,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  retryAutomationRun,
  type Automation,
  type AutomationNotification,
  type AutomationRun,
  type IntegrationConnection,
  type NotificationList,
} from "../../lib/automation-api";
import styles from "./automations.module.css";
import { IntegrationPanel } from "./integration-panel";
import { TaskPanel } from "./task-panel";

type WorkspaceTab = "tasks" | "runs" | "integrations" | "notifications";

const TABS: Array<{ id: WorkspaceTab; label: string }> = [
  { id: "tasks", label: "Tasks" },
  { id: "runs", label: "Runs" },
  { id: "integrations", label: "Integrations" },
  { id: "notifications", label: "Notifications" },
];

function formatDate(value: string | null): string {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AutomationWorkspace({
  initialAutomations,
  initialRuns,
  initialIntegrations,
  initialNotifications,
  models,
  personas,
  initialAutomationId,
}: {
  initialAutomations: Automation[];
  initialRuns: AutomationRun[];
  initialIntegrations: IntegrationConnection[];
  initialNotifications: NotificationList;
  models: CachedModel[];
  personas: Persona[];
  initialAutomationId: string | null;
}) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("tasks");
  const [taskToOpen, setTaskToOpen] = useState(initialAutomationId);
  const [automations, setAutomations] = useState(initialAutomations);
  const [runs, setRuns] = useState(initialRuns);
  const [integrations, setIntegrations] = useState(initialIntegrations);
  const [notifications, setNotifications] = useState(initialNotifications.items);
  const [unreadCount, setUnreadCount] = useState(initialNotifications.unread_count);

  function selectTab(tab: WorkspaceTab, focus = false) {
    setActiveTab(tab);
    if (focus) {
      tabRefs.current[TABS.findIndex((item) => item.id === tab)]?.focus();
    }
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % TABS.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + TABS.length) % TABS.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = TABS.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    selectTab(TABS[nextIndex].id, true);
  }

  return (
    <div className={styles.workspace}>
      <div className={styles.tabs} aria-label="Task sections" role="tablist">
        {TABS.map((tab, index) => (
          <button
            aria-controls={`task-panel-${tab.id}`}
            aria-selected={activeTab === tab.id}
            className={activeTab === tab.id ? styles.activeTab : ""}
            id={`task-tab-${tab.id}`}
            key={tab.id}
            onClick={() => selectTab(tab.id)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
            ref={(element) => {
              tabRefs.current[index] = element;
            }}
            role="tab"
            tabIndex={activeTab === tab.id ? 0 : -1}
            type="button"
          >
            {tab.label}
            {tab.id === "notifications" && unreadCount > 0 ? (
              <span>{unreadCount}</span>
            ) : null}
          </button>
        ))}
      </div>

      {activeTab === "tasks" ? (
        <section
          aria-labelledby="task-tab-tasks"
          className={styles.tabPanel}
          id="task-panel-tasks"
          role="tabpanel"
          tabIndex={0}
        >
          <TaskPanel
            automations={automations}
            initialAutomationId={taskToOpen}
            integrations={integrations}
            models={models}
            onAutomationsChange={setAutomations}
            onRunsChange={setRuns}
            personas={personas}
            runs={runs}
          />
        </section>
      ) : null}

      {activeTab === "runs" ? (
        <section
          aria-labelledby="task-tab-runs"
          className={styles.tabPanel}
          id="task-panel-runs"
          role="tabpanel"
          tabIndex={0}
        >
          <RunsPanel
            runs={runs}
            onRunsChange={setRuns}
            onOpenTask={(taskId) => {
              setTaskToOpen(taskId);
              selectTab("tasks", true);
              window.history.replaceState(null, "", `/tasks?task=${taskId}`);
            }}
          />
        </section>
      ) : null}

      {activeTab === "integrations" ? (
        <section
          aria-labelledby="task-tab-integrations"
          className={styles.tabPanel}
          id="task-panel-integrations"
          role="tabpanel"
          tabIndex={0}
        >
          <IntegrationPanel
            integrations={integrations}
            onIntegrationsChange={setIntegrations}
          />
        </section>
      ) : null}

      {activeTab === "notifications" ? (
        <section
          aria-labelledby="task-tab-notifications"
          className={styles.tabPanel}
          id="task-panel-notifications"
          role="tabpanel"
          tabIndex={0}
        >
          <NotificationsPanel
            notifications={notifications}
            onNotificationsChange={(items, count) => {
              setNotifications(items);
              setUnreadCount(count);
            }}
          />
        </section>
      ) : null}
    </div>
  );
}

function RunsPanel({
  runs,
  onRunsChange,
  onOpenTask,
}: {
  runs: AutomationRun[];
  onRunsChange: (runs: AutomationRun[]) => void;
  onOpenTask: (taskId: string) => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(runs[0]?.id ?? null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = runs.find((item) => item.id === selectedId) ?? runs[0] ?? null;

  async function refresh() {
    const next = await listAutomationRuns();
    onRunsChange(next);
    if (selectedId && !next.some((item) => item.id === selectedId)) {
      setSelectedId(next[0]?.id ?? null);
    }
  }

  async function act(action: "cancel" | "retry") {
    if (!selected) return;
    setBusy(action);
    setError(null);
    try {
      if (action === "cancel") await cancelAutomationRun(selected.id);
      else await retryAutomationRun(selected.id);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not ${action} the run.`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={styles.twoPanel}>
      <aside aria-label="Task run history" className={styles.sideList}>
        <button className={styles.refreshButton} onClick={() => void refresh()} type="button">
          Refresh history
        </button>
        {runs.map((run) => (
          <button
            aria-pressed={selected?.id === run.id}
            className={selected?.id === run.id ? styles.selectedItem : ""}
            key={run.id}
            onClick={() => setSelectedId(run.id)}
            type="button"
          >
            <span
              aria-hidden="true"
              className={`${styles.statusDot} ${styles[`status_${run.status}`]}`}
            />
            <div>
              <strong>{run.automation_name}</strong>
              <span>
                {run.status} · {formatDate(run.created_at)}
              </span>
            </div>
          </button>
        ))}
      </aside>

      <section className={styles.detailPanel}>
        {!selected ? (
          <div className={styles.emptyState}>No task runs yet.</div>
        ) : (
          <>
            <header className={styles.detailHeader}>
              <div>
                <p>Run detail</p>
                <h2>{selected.automation_name}</h2>
                <span>
                  {selected.trigger_source} · {formatDate(selected.scheduled_for)}
                </span>
              </div>
              <div className={styles.headerActions}>
                <button onClick={() => onOpenTask(selected.automation_id)} type="button">
                  Open task
                </button>
                {selected.status === "queued" ? (
                  <button disabled={Boolean(busy)} onClick={() => void act("cancel")} type="button">
                    Cancel
                  </button>
                ) : null}
                {selected.status === "failed" || selected.status === "completed_with_errors" ? (
                  <button disabled={Boolean(busy)} onClick={() => void act("retry")} type="button">
                    Retry
                  </button>
                ) : null}
              </div>
            </header>
            {error ? (
              <div className={styles.error} role="alert">
                {error}
              </div>
            ) : null}
            <div className={styles.summaryGrid}>
              <Metric label="Status" value={selected.status} />
              <Metric label="Attempt" value={`${selected.attempt}/${selected.max_attempts}`} />
              <Metric label="Model" value={selected.provider_model_id ?? "Not started"} />
              <Metric label="Persona" value={selected.persona_name ?? "None"} />
              <Metric label="Started" value={formatDate(selected.started_at)} />
              <Metric label="Finished" value={formatDate(selected.finished_at)} />
            </div>
            <DetailBlock label="Task instruction snapshot" value={selected.instruction_snapshot} />
            <DetailBlock
              label="Trigger payload"
              value={JSON.stringify(selected.trigger_payload, null, 2)}
              code
            />
            <DetailBlock
              label="Result"
              value={selected.response || selected.error_message || "No output yet."}
            />
            <section className={styles.deliveryAttempts}>
              <div className={styles.sectionTitle}>
                <p>Delivery history</p>
                <h3>External side effects</h3>
              </div>
              {selected.deliveries.length === 0 ? (
                <div className={styles.emptyDelivery}>No delivery attempts.</div>
              ) : (
                selected.deliveries.map((delivery) => (
                  <article key={delivery.id}>
                    <div>
                      <strong>{delivery.channel}</strong>
                      <span>{delivery.status}</span>
                    </div>
                    <p>
                      {delivery.destination || delivery.error_message || "No destination recorded."}
                    </p>
                  </article>
                ))
              )}
            </section>
          </>
        )}
      </section>
    </div>
  );
}

function NotificationsPanel({
  notifications,
  onNotificationsChange,
}: {
  notifications: AutomationNotification[];
  onNotificationsChange: (items: AutomationNotification[], unreadCount: number) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const result = await listNotifications();
    onNotificationsChange(result.items, result.unread_count);
  }

  async function act(name: "read" | "delete" | "read-all", id?: string) {
    setBusy(`${name}-${id ?? "all"}`);
    setError(null);
    try {
      if (name === "read-all") await markAllNotificationsRead();
      else if (name === "read" && id) await markNotificationRead(id);
      else if (name === "delete" && id) await deleteNotification(id);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The notification action failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className={styles.singlePanel}>
      <header className={styles.detailHeader}>
        <div>
          <p>Private inbox</p>
          <h2>Task notifications</h2>
          <span>Success, failure, and fast-reply notices stay inside Aster.</span>
        </div>
        <div className={styles.headerActions}>
          <button onClick={() => void refresh()} type="button">
            Refresh
          </button>
          <button disabled={Boolean(busy)} onClick={() => void act("read-all")} type="button">
            Mark all read
          </button>
        </div>
      </header>
      {error ? (
        <div className={styles.error} role="alert">
          {error}
        </div>
      ) : null}
      <div className={styles.notificationList}>
        {notifications.length === 0 ? (
          <div className={styles.emptyState}>No notifications.</div>
        ) : (
          notifications.map((notification) => (
            <article
              className={notification.read_at ? styles.readNotification : ""}
              key={notification.id}
            >
              <span
                aria-hidden="true"
                className={`${styles.notificationLevel} ${styles[notification.level]}`}
              />
              <div>
                <header>
                  <strong>{notification.title}</strong>
                  <time>{formatDate(notification.created_at)}</time>
                </header>
                <p>{notification.body}</p>
                <div className={styles.notificationActions}>
                  {!notification.read_at ? (
                    <button
                      disabled={Boolean(busy)}
                      onClick={() => void act("read", notification.id)}
                      type="button"
                    >
                      Mark read
                    </button>
                  ) : null}
                  <button
                    disabled={Boolean(busy)}
                    onClick={() => void act("delete", notification.id)}
                    type="button"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DetailBlock({
  label,
  value,
  code = false,
}: {
  label: string;
  value: string;
  code?: boolean;
}) {
  return (
    <section className={styles.detailBlock}>
      <span>{label}</span>
      {code ? <pre>{value}</pre> : <p>{value}</p>}
    </section>
  );
}
