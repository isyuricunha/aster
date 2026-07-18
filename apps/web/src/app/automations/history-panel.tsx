"use client";

import { useState } from "react";

import {
  cancelAutomationRun,
  deleteNotification,
  listAutomationRuns,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  retryAutomationRun,
  type AutomationRun,
  type NotificationList,
} from "../../lib/automation-api";
import { Icon } from "../ui/icons";
import styles from "./automations.module.css";

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

export function AutomationHistory({
  runs,
  onRunsChange,
  notifications,
  onNotificationsChange,
}: {
  runs?: AutomationRun[];
  onRunsChange?: (items: AutomationRun[]) => void;
  notifications?: NotificationList;
  onNotificationsChange?: (items: NotificationList) => void;
}) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(runs?.[0]?.id ?? null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedRun = runs?.find((run) => run.id === selectedRunId) ?? null;

  async function cancel(run: AutomationRun) {
    if (!onRunsChange || working) return;
    setWorking(true);
    setError(null);
    try {
      await cancelAutomationRun(run.id);
      onRunsChange(await listAutomationRuns());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not cancel the run.");
    } finally {
      setWorking(false);
    }
  }

  async function retry(run: AutomationRun) {
    if (!onRunsChange || working) return;
    setWorking(true);
    setError(null);
    try {
      const created = await retryAutomationRun(run.id);
      const next = await listAutomationRuns();
      onRunsChange(next);
      setSelectedRunId(created.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not retry the run.");
    } finally {
      setWorking(false);
    }
  }

  async function readNotification(id: string) {
    if (!onNotificationsChange) return;
    await markNotificationRead(id);
    onNotificationsChange(await listNotifications());
  }

  async function removeNotification(id: string) {
    if (!onNotificationsChange) return;
    await deleteNotification(id);
    onNotificationsChange(await listNotifications());
  }

  async function readAll() {
    if (!onNotificationsChange) return;
    await markAllNotificationsRead();
    onNotificationsChange(await listNotifications());
  }

  if (notifications && onNotificationsChange) {
    return (
      <section className={styles.activitySection}>
        <header className={styles.activityHeader}><div><p>Inbox</p><h2>Private notifications</h2><span>{notifications.unread_count} unread of {notifications.total}</span></div><button disabled={!notifications.unread_count} onClick={() => void readAll()} type="button">Mark all read</button></header>
        {notifications.items.length === 0 ? <div className={styles.emptyState}><Icon name="chat" size={26} /><strong>No notifications yet.</strong><span>Automation successes and failures appear here according to each policy.</span></div> : <div className={styles.notificationList}>{notifications.items.map((item) => <article className={item.read_at ? "" : styles.unread} key={item.id}><div className={`${styles.levelDot} ${styles[item.level]}`} /><div><header><strong>{item.title}</strong><span>{formatDate(item.created_at)}</span></header><p>{item.body}</p><footer>{!item.read_at ? <button onClick={() => void readNotification(item.id)} type="button">Mark read</button> : null}<button onClick={() => void removeNotification(item.id)} type="button">Delete</button></footer></div></article>)}</div>}
      </section>
    );
  }

  return (
    <section className={styles.activitySection}>
      {error ? <div className={styles.error}>{error}</div> : null}
      <header className={styles.activityHeader}><div><p>Audit history</p><h2>Automation runs</h2><span>{runs?.length ?? 0} recent runs</span></div><button onClick={() => onRunsChange && void listAutomationRuns().then(onRunsChange)} type="button"><Icon name="refresh" size={13} /> Refresh</button></header>
      {!runs?.length ? <div className={styles.emptyState}><Icon name="refresh" size={26} /><strong>No runs yet.</strong><span>Use Run now or wait for the next scheduled occurrence.</span></div> : <div className={styles.runLayout}><div className={styles.runList}>{runs.map((run) => <button className={selectedRunId === run.id ? styles.selectedRun : ""} key={run.id} onClick={() => setSelectedRunId(run.id)} type="button"><span className={`${styles.statusDot} ${styles[run.status]}`} /><div><strong>{run.automation_name}</strong><span>{run.status} · {run.trigger_source} · attempt {run.attempt}/{run.max_attempts}</span><small>{formatDate(run.created_at)}</small></div></button>)}</div>{selectedRun ? <aside className={styles.runDetails}><header><div><span>{selectedRun.trigger_source}</span><h3>{selectedRun.status}</h3></div><div>{selectedRun.status === "queued" ? <button disabled={working} onClick={() => void cancel(selectedRun)} type="button">Cancel</button> : null}{selectedRun.status === "failed" ? <button disabled={working} onClick={() => void retry(selectedRun)} type="button">Retry</button> : null}</div></header><dl><div><dt>Scheduled for</dt><dd>{formatDate(selectedRun.scheduled_for)}</dd></div><div><dt>Model</dt><dd>{selectedRun.provider_model_id ?? "Not reached"}</dd></div><div><dt>Persona</dt><dd>{selectedRun.persona_name ?? "None"}</dd></div><div><dt>Instruction</dt><dd>{selectedRun.instruction_snapshot}</dd></div>{Object.keys(selectedRun.trigger_payload).length ? <div><dt>Trigger payload</dt><dd><code>{JSON.stringify(selectedRun.trigger_payload, null, 2)}</code></dd></div> : null}{selectedRun.response ? <div><dt>Result</dt><dd className={styles.result}>{selectedRun.response}</dd></div> : null}{selectedRun.error_message ? <div><dt>Error</dt><dd>{selectedRun.error_message}</dd></div> : null}</dl>{selectedRun.deliveries.length ? <div className={styles.attempts}><strong>Deliveries</strong>{selectedRun.deliveries.map((attempt) => <div key={attempt.id}><span>{attempt.channel}</span><span>{attempt.status}</span><small>{attempt.destination ?? attempt.error_message ?? "Pending"}</small></div>)}</div> : null}</aside> : null}</div>}
    </section>
  );
}
