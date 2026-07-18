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

  async function refresh() {
    const result = await listAgentNotifications();
    onNotificationsChange(result.items, result.unread_count);
  }

  async function act(action: "read" | "delete" | "read-all", id?: string) {
    setWorking(`${action}-${id ?? "all"}`);
    setError(null);
    try {
      if (action === "read-all") await markAllAgentNotificationsRead();
      else if (action === "read" && id) await markAgentNotificationRead(id);
      else if (action === "delete" && id) await deleteAgentNotification(id);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The notification action failed.");
    } finally {
      setWorking(null);
    }
  }

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <div>
          <p>Owner inbox</p>
          <h2>Agent notifications</h2>
          <span className={styles.muted}>Completion and failure notices stay inside the private workspace.</span>
        </div>
        <div className={styles.headerActions}>
          <button onClick={() => void refresh()} type="button">Refresh</button>
          <button disabled={Boolean(working)} onClick={() => void act("read-all")} type="button">Mark all read</button>
        </div>
      </header>
      {error ? <div className={styles.error}>{error}</div> : null}
      <div className={styles.notificationList}>
        {notifications.length === 0 ? <div className={styles.empty}>No agent notifications.</div> : notifications.map((item) => (
          <article key={item.id}>
            <div className={styles.notificationHeader}>
              <div><strong>{item.title}</strong><div className={styles.itemMeta}>{formatDate(item.created_at)}</div></div>
              <span className={styles.status} data-status={item.level === "error" ? "failed" : "completed"}>{item.level}</span>
            </div>
            <div className={styles.output}>{item.body}</div>
            <div className={styles.headerActions}>
              {!item.read_at ? <button disabled={Boolean(working)} onClick={() => void act("read", item.id)} type="button">Mark read</button> : null}
              <button disabled={Boolean(working)} onClick={() => void act("delete", item.id)} type="button">Delete</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
