"use client";

import { useState } from "react";

import { setAgentControl, type AgentRun } from "../../lib/agent-api";
import { AgentEditor } from "./agent-editor";
import { NotificationPanel } from "./notification-panel";
import type { InitialAgentData } from "./page";
import { RulePanel } from "./rule-panel";
import { RunPanel } from "./run-panel";
import styles from "./agents.module.css";

type WorkspaceTab = "agents" | "runs" | "rules" | "notifications";

const TABS: Array<{ id: WorkspaceTab; label: string }> = [
  { id: "agents", label: "Agents" },
  { id: "runs", label: "Runs & approvals" },
  { id: "rules", label: "Event rules" },
  { id: "notifications", label: "Notifications" },
];

export function AgentWorkspace({ initial }: { initial: InitialAgentData }) {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("agents");
  const [agents, setAgents] = useState(initial.agents);
  const [runs, setRuns] = useState(initial.runs);
  const [rules, setRules] = useState(initial.rules);
  const [notifications, setNotifications] = useState(initial.notifications.items);
  const [unreadCount, setUnreadCount] = useState(initial.notifications.unread_count);
  const [control, setControl] = useState(initial.control);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(initial.agents[0]?.id ?? null);
  const [controlBusy, setControlBusy] = useState(false);
  const [controlError, setControlError] = useState<string | null>(initial.error);

  function addRun(run: AgentRun) {
    setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
    setActiveTab("runs");
  }

  async function toggleEmergencyStop() {
    if (controlBusy) return;
    const enabling = !control.emergency_stop;
    const reason = enabling
      ? window.prompt(
          "Reason for stopping every autonomous agent run:",
          "Emergency stop activated by the owner.",
        )
      : "";
    if (enabling && reason === null) return;
    setControlBusy(true);
    setControlError(null);
    try {
      const updated = await setAgentControl(enabling, reason ?? "");
      setControl(updated);
      if (enabling) {
        setRuns((current) =>
          current.map((run) =>
            ["queued", "running", "waiting_approval", "paused"].includes(run.status)
              ? {
                  ...run,
                  status: "cancelled",
                  cancel_requested: true,
                  error_code: "emergency_stop",
                  error_message: updated.reason,
                }
              : run,
          ),
        );
      }
    } catch (caught) {
      setControlError(caught instanceof Error ? caught.message : "Could not update the emergency stop.");
    } finally {
      setControlBusy(false);
    }
  }

  return (
    <div className={styles.workspace}>
      <section className={styles.controlBar} data-stopped={control.emergency_stop}>
        <div className={styles.controlCopy}>
          <strong>{control.emergency_stop ? "Emergency stop active" : "Autonomous execution enabled"}</strong>
          <span>
            {control.emergency_stop
              ? control.reason || "Every queued or active run has been cancelled."
              : "Agents remain constrained by their frozen scopes, approvals, and hard budgets."}
          </span>
        </div>
        <button
          className={control.emergency_stop ? styles.primary : styles.danger}
          disabled={controlBusy}
          onClick={() => void toggleEmergencyStop()}
          type="button"
        >
          {controlBusy ? "Updating…" : control.emergency_stop ? "Release emergency stop" : "Stop all agents"}
        </button>
      </section>

      {controlError ? <div className={styles.error}>{controlError}</div> : null}

      <nav className={styles.tabs} aria-label="Autonomous agent sections">
        {TABS.map((tab) => (
          <button
            aria-current={activeTab === tab.id ? "page" : undefined}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            {tab.label}
            {tab.id === "notifications" && unreadCount > 0 ? ` (${unreadCount})` : ""}
          </button>
        ))}
      </nav>

      {activeTab === "agents" ? (
        <AgentEditor
          accounts={initial.accounts}
          agents={agents}
          collections={initial.collections}
          disabled={control.emergency_stop}
          models={initial.models}
          onAgentsChange={setAgents}
          onRunsChange={addRun}
          onSelect={setSelectedAgentId}
          personas={initial.personas}
          selectedId={selectedAgentId}
          tools={initial.tools}
        />
      ) : null}

      {activeTab === "runs" ? <RunPanel onRunsChange={setRuns} runs={runs} /> : null}

      {activeTab === "rules" ? (
        <RulePanel
          accounts={initial.accounts}
          agents={agents}
          onRulesChange={setRules}
          rules={rules}
        />
      ) : null}

      {activeTab === "notifications" ? (
        <NotificationPanel
          notifications={notifications}
          onNotificationsChange={(items, unread) => {
            setNotifications(items);
            setUnreadCount(unread);
          }}
        />
      ) : null}
    </div>
  );
}
