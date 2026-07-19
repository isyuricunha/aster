"use client";

import { useEffect, useState, type ReactNode } from "react";

import styles from "./simple-settings.module.css";

export const SETTINGS_UPDATED_EVENT = "aster:settings-updated";

export function notifySettingsUpdated(): void {
  window.dispatchEvent(new Event(SETTINGS_UPDATED_EVENT));
}

export function useUnsavedChanges(dirty: boolean): void {
  useEffect(() => {
    if (!dirty) return;
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [dirty]);
}

export function SummaryGrid({ children }: { children: ReactNode }) {
  return <div className={styles.summaryGrid}>{children}</div>;
}

export function SummaryCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className={styles.summaryCard}>
      <span>{label}</span>
      <strong title={value}>{value}</strong>
      {note ? <small>{note}</small> : null}
    </div>
  );
}

export function UnsavedBadge({ visible }: { visible: boolean }) {
  return visible ? <span className={styles.unsaved}>Unsaved changes</span> : null;
}

export function AdvancedSettings({
  title = "Advanced settings",
  description = "Technical controls, maintenance actions, imports, exports, and per-conversation overrides.",
  children,
}: {
  title?: string;
  description?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const close = () => setOpen(false);
    window.addEventListener(SETTINGS_UPDATED_EVENT, close);
    return () => window.removeEventListener(SETTINGS_UPDATED_EVENT, close);
  }, []);

  return (
    <section className={styles.advanced}>
      <button
        aria-expanded={open}
        className={styles.advancedToggle}
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span>
          <strong>{title}</strong>
          <small>{description}</small>
        </span>
        <span
          aria-hidden="true"
          className={`${styles.advancedChevron} ${open ? styles.advancedChevronOpen : ""}`}
        >
          ▶
        </span>
      </button>
      {open ? <div className={styles.advancedBody}>{children}</div> : null}
    </section>
  );
}
