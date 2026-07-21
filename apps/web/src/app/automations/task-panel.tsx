"use client";

import { useMemo, useState } from "react";

import type { CachedModel, Persona } from "../../lib/api";
import {
  listAutomationRuns,
  listTasks,
  runTask,
  setTaskEnabled,
  type Automation,
  type AutomationRun,
  type IntegrationConnection,
} from "../../lib/automation-api";
import { Icon } from "../ui/icons";
import { AutomationPanel } from "./automation-panel";
import styles from "./tasks.module.css";

type TaskPanelProps = {
  automations: Automation[];
  runs: AutomationRun[];
  models: CachedModel[];
  personas: Persona[];
  integrations: IntegrationConnection[];
  initialAutomationId: string | null;
  onAutomationsChange: (items: Automation[]) => void;
  onRunsChange: (items: AutomationRun[]) => void;
};

function formatDate(value: string | null): string {
  if (!value) return "Not yet";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function scheduleLabel(task: Automation): string {
  const display = task.schedule.display_schedule ?? task.state.display_schedule;
  if (typeof display === "string" && display.trim()) return display;
  if (task.trigger_type === "interval") {
    const seconds = task.schedule.interval_seconds;
    if (typeof seconds === "number") {
      if (seconds % 3600 === 0) {
        const hours = seconds / 3600;
        return hours === 1 ? "Every hour" : `Every ${hours} hours`;
      }
      if (seconds % 60 === 0) return `Every ${seconds / 60} minutes`;
    }
  }
  return task.trigger_type;
}

function cronLabel(task: Automation): string | null {
  const display = task.schedule.display_cron ?? task.state.display_cron;
  return typeof display === "string" && display.trim() ? display : null;
}

function availability(task: Automation): "ready" | "requires_skills" {
  return task.state.availability === "requires_skills" ? "requires_skills" : "ready";
}

export function TaskPanel({
  automations,
  runs,
  models,
  personas,
  integrations,
  initialAutomationId,
  onAutomationsChange,
  onRunsChange,
}: TaskPanelProps) {
  const builtins = useMemo(
    () => automations.filter((task) => Boolean(task.builtin_key)),
    [automations],
  );
  const customTasks = useMemo(
    () => automations.filter((task) => !task.builtin_key),
    [automations],
  );
  const initialBuiltin =
    builtins.find((task) => task.id === initialAutomationId) ?? builtins[0] ?? null;
  const [selectedBuiltinId, setSelectedBuiltinId] = useState<string | null>(
    initialBuiltin?.id ?? null,
  );
  const [showCustomTasks, setShowCustomTasks] = useState(
    Boolean(initialAutomationId && customTasks.some((task) => task.id === initialAutomationId)),
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selected = builtins.find((task) => task.id === selectedBuiltinId) ?? builtins[0] ?? null;
  const selectedRuns = selected
    ? runs.filter((run) => run.automation_id === selected.id)
    : [];

  async function refresh() {
    const [nextTasks, nextRuns] = await Promise.all([listTasks(), listAutomationRuns()]);
    onAutomationsChange(nextTasks);
    onRunsChange(nextRuns);
  }

  async function act(action: "toggle" | "run") {
    if (!selected || busy) return;
    setBusy(action);
    setNotice(null);
    setError(null);
    try {
      if (action === "toggle") {
        await setTaskEnabled(selected.id, !selected.enabled);
        setNotice(selected.enabled ? "Task paused." : "Task activated.");
      } else {
        await runTask(selected.id);
        setNotice("Task run queued.");
      }
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The task action failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={styles.taskWorkspace}>
      <aside aria-label="Tasks" className={styles.taskList}>
        <header>
          <div>
            <strong>Built-in tasks</strong>
            <span>{builtins.length} maintained by Aster</span>
          </div>
        </header>
        <div className={styles.taskItems}>
          {builtins.map((task) => {
            const unavailable = availability(task) === "requires_skills";
            return (
              <button
                aria-pressed={!showCustomTasks && selected?.id === task.id}
                className={!showCustomTasks && selected?.id === task.id ? styles.selectedTask : ""}
                key={task.id}
                onClick={() => {
                  setSelectedBuiltinId(task.id);
                  setShowCustomTasks(false);
                  setNotice(null);
                  setError(null);
                }}
                type="button"
              >
                <span
                  aria-hidden="true"
                  className={`${styles.statusDot} ${
                    unavailable
                      ? styles.unavailableDot
                      : task.enabled
                        ? styles.activeDot
                        : styles.pausedDot
                  }`}
                />
                <div>
                  <strong>{task.name}</strong>
                  <span>{scheduleLabel(task)}</span>
                </div>
                <small>{unavailable ? "Waiting" : task.enabled ? "Active" : "Paused"}</small>
              </button>
            );
          })}
        </div>
        <button
          aria-pressed={showCustomTasks}
          className={`${styles.customTasksButton} ${showCustomTasks ? styles.selectedTask : ""}`}
          onClick={() => {
            setShowCustomTasks(true);
            setNotice(null);
            setError(null);
          }}
          type="button"
        >
          <Icon name="edit" size={15} />
          <div>
            <strong>Custom tasks</strong>
            <span>{customTasks.length} owner-defined</span>
          </div>
        </button>
      </aside>

      <section className={styles.taskDetail}>
        {showCustomTasks ? (
          <div className={styles.customTaskSurface}>
            <header className={styles.customTaskHeader}>
              <p>Owner-defined work</p>
              <h2>Custom tasks</h2>
              <span>Create scheduled model tasks and explicit integration deliveries.</span>
            </header>
            <AutomationPanel
              automations={customTasks}
              initialAutomationId={
                initialAutomationId && customTasks.some((task) => task.id === initialAutomationId)
                  ? initialAutomationId
                  : null
              }
              integrations={integrations}
              models={models}
              onAutomationsChange={(nextCustomTasks) => {
                const nextBuiltins = automations.filter((task) => Boolean(task.builtin_key));
                onAutomationsChange([...nextBuiltins, ...nextCustomTasks]);
              }}
              onRunsChange={onRunsChange}
              personas={personas}
              runs={runs}
            />
          </div>
        ) : !selected ? (
          <div className={styles.emptyState}>Built-in tasks are being initialized.</div>
        ) : (
          <>
            <header className={styles.detailHeader}>
              <div>
                <div className={styles.badges}>
                  <span>Built-in</span>
                  <span
                    className={
                      availability(selected) === "requires_skills"
                        ? styles.waitingBadge
                        : selected.enabled
                          ? styles.activeBadge
                          : styles.pausedBadge
                    }
                  >
                    {availability(selected) === "requires_skills"
                      ? "Waiting for Skills"
                      : selected.enabled
                        ? "Active"
                        : "Paused"}
                  </span>
                </div>
                <h2>{selected.name}</h2>
                <p>{selected.description}</p>
              </div>
              <div className={styles.actions}>
                <button
                  disabled={Boolean(busy) || availability(selected) === "requires_skills"}
                  onClick={() => void act("toggle")}
                  type="button"
                >
                  {busy === "toggle"
                    ? "Saving…"
                    : selected.enabled
                      ? "Pause"
                      : "Activate"}
                </button>
                <button
                  className={styles.runButton}
                  disabled={Boolean(busy) || availability(selected) === "requires_skills"}
                  onClick={() => void act("run")}
                  type="button"
                >
                  <Icon name="refresh" size={14} />
                  {busy === "run" ? "Queueing…" : "Run now"}
                </button>
              </div>
            </header>

            {notice ? <div className={styles.notice}>{notice}</div> : null}
            {error ? <div className={styles.error}>{error}</div> : null}

            <div className={styles.metrics}>
              <article>
                <span>Schedule</span>
                <strong>{scheduleLabel(selected)}</strong>
                {cronLabel(selected) ? <small>Cron: {cronLabel(selected)}</small> : null}
              </article>
              <article>
                <span>Next run</span>
                <strong>{selected.enabled ? formatDate(selected.next_run_at) : "Paused"}</strong>
              </article>
              <article>
                <span>Last run</span>
                <strong>{formatDate(selected.last_run_at)}</strong>
              </article>
              <article>
                <span>Runs</span>
                <strong>{selectedRuns.length}</strong>
              </article>
            </div>

            {availability(selected) === "requires_skills" ? (
              <section className={styles.waitingPanel}>
                <Icon name="tools" size={18} />
                <div>
                  <strong>Reserved for the future Skills system</strong>
                  <p>
                    Aster currently has Tools/MCP, not first-class Skills. This task stays visible
                    and disabled rather than pretending those are the same thing.
                  </p>
                </div>
              </section>
            ) : null}

            <section className={styles.behaviorPanel}>
              <span>What this task does</span>
              <p>{selected.instruction}</p>
            </section>

            <section className={styles.behaviorPanel}>
              <span>Latest result</span>
              <p>
                {typeof selected.state.last_result === "string"
                  ? selected.state.last_result
                  : "No completed result yet."}
              </p>
            </section>

            <section className={styles.recentRuns}>
              <header>
                <div>
                  <span>Recent activity</span>
                  <strong>{selected.name}</strong>
                </div>
              </header>
              {selectedRuns.length ? (
                selectedRuns.slice(0, 8).map((run) => (
                  <article key={run.id}>
                    <span className={`${styles.runStatus} ${styles[`run_${run.status}`]}`} />
                    <div>
                      <strong>{run.status.replaceAll("_", " ")}</strong>
                      <span>{formatDate(run.created_at)}</span>
                    </div>
                    <p>{run.response || run.error_message || "Waiting for the worker."}</p>
                  </article>
                ))
              ) : (
                <div className={styles.emptyRuns}>No runs yet.</div>
              )}
            </section>
          </>
        )}
      </section>
    </div>
  );
}
