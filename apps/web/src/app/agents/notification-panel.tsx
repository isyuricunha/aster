"use client";

import { useState } from "react";

import {
  deleteAgentNotification,
  listAgentNotifications,
  markAgentNotificationRead,
  markAllAgentNotificationsRead,
  type AgentNotification,
} from "../../lib/agent-api";
import styles from "./agents.module.css";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function NotificationPanel({
  notifications,
  onNotificationsChange,
}: {
  notifications: AgentNotification[];
  onNotificationsChange: (items: AgentNotification[], unread: number) => void;
}) {
  const [working, setWorking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    const result = await listAgentNotifications();
    onNotificationsChange(result.items, result.unread_count);
  }

  async function refreshNotifications() {
    if (working) return;
    setWorking("refresh-all");
    setError(null);
    setMessage(null);
    try {
      await refresh();
      setMessage("Agent notifications refreshed.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not refresh agent notifications.");
    } finally {
      setWorking(null);
    }
  }

  async function act(action: "read" | "delete" | "read-all", id?: string) {
    if (working) return;
    const notification = id ? notifications.find((item) => item.id === id) : null;
    if (
      action === "delete" &&
      notification &&
      !window.confirm(`Delete notification "${notification.title}"? This cannot be undone.`)
    ) {
      return;
    }
    setWorking(`${action}-${id ?? "all"}`);
    setError(null);
    setMessage(null);
    try {
      if (action === "read-all") await markAllAgentNotificationsRead();
      else if (action === "read" && id) await markAgentNotificationRead(id);
      else if (action === "delete" && id) await deleteAgentNotification(id);
      await refresh();
      setMessage(
        action === "read-all"
          ? "All notifications marked as read."
          : action === "read"
            ? "Notification marked as read."
            : "Notification deleted.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The notification action failed.");
    } finally {
      setWorking(null);
    }
  }

  return (
    <section aria-busy={Boolean(working)} aria-labelledby="agent-notifications-title" className={styles.panel}>
      <header className={styles.panelHeader}>
        <div>
          <p>Owner inbox</p>
          <h2 id="agent-notifications-title">Agent notifications</h2>
          <span className={styles.muted}>Completion and failure notices stay inside the private workspace.</span>
        </div>
        <div className={styles.headerActions}>
          <button disabled={Boolean(working)} onClick={() => void refreshNotifications()} type="button">
            {working === "refresh-all" ? "Refreshing…" : "Refresh"}
          </button>
          <button disabled={Boolean(working) || notifications.every((item) => Boolean(item.read_at))} onClick={() => void act("read-all")} type="button">
            {working === "read-all-all" ? "Marking all read…" : "Mark all read"}
          </button>
        </div>
      </header>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}
      {message ? <div className={styles.success} role="status">{message}</div> : null}
      <div className={styles.notificationList}>
        {notifications.length === 0 ? <div className={styles.empty} role="status">No agent notifications.</div> : notifications.map((item) => (
          <article aria-label={`${item.read_at ? "Read" : "Unread"} notification: ${item.title}`} data-unread={!item.read_at} key={item.id}>
            <div className={styles.notificationHeader}>
              <div><strong>{item.title}</strong><div className={styles.itemMeta}>{formatDate(item.created_at)}</div></div>
              <span className={styles.status} data-status={item.level === "error" ? "failed" : "completed"}>{item.level}</span>
            </div>
            <div className={styles.output}>{item.body}</div>
            <div className={styles.headerActions}>
              {!item.read_at ? <button aria-label={`Mark ${item.title} as read`} disabled={Boolean(working)} onClick={() => void act("read", item.id)} type="button">{working === `read-${item.id}` ? "Marking read…" : "Mark read"}</button> : null}
              <button aria-label={`Delete ${item.title}`} className={styles.danger} disabled={Boolean(working)} onClick={() => void act("delete", item.id)} type="button">{working === `delete-${item.id}` ? "Deleting notification…" : "Delete notification"}</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
