"use client";

import { useRef, useState, type KeyboardEvent } from "react";

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
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
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

  function selectTab(tab: WorkspaceTab, focus = false) {
    setActiveTab(tab);
    if (focus) {
      const nextIndex = TABS.findIndex((item) => item.id === tab);
      tabRefs.current[nextIndex]?.focus();
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

  async function toggleEmergencyStop() {
    if (controlBusy) return;
    const enabling = !control.emergency_stop;
    if (
      enabling &&
      !window.confirm(
        "Activate the emergency stop? Every queued or active agent run will be cancelled, and agent changes will be blocked until you release it.",
      )
    ) {
      return;
    }
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
      <section
        aria-busy={controlBusy}
        aria-labelledby="agent-control-title"
        className={styles.controlBar}
        data-stopped={control.emergency_stop}
      >
        <div className={styles.controlCopy}>
          <strong id="agent-control-title">
            {control.emergency_stop ? "Emergency stop active" : "Autonomous execution enabled"}
          </strong>
          <span aria-live="polite" id="agent-control-description">
            {control.emergency_stop
              ? control.reason || "Every queued or active run has been cancelled."
              : "Agents remain constrained by their frozen scopes, approvals, and hard budgets."}
          </span>
        </div>
        <button
          className={control.emergency_stop ? styles.primary : styles.danger}
          disabled={controlBusy}
          aria-describedby="agent-control-description"
          aria-pressed={control.emergency_stop}
          onClick={() => void toggleEmergencyStop()}
          type="button"
        >
          {controlBusy
            ? control.emergency_stop
              ? "Releasing emergency stop…"
              : "Stopping active runs…"
            : control.emergency_stop
              ? "Release emergency stop"
              : "Stop all active runs"}
        </button>
      </section>

      {controlError ? <div className={styles.error} role="alert">{controlError}</div> : null}

      <div className={styles.tabs} aria-label="Autonomous agent sections" role="tablist">
        {TABS.map((tab, index) => (
          <button
            aria-controls={`agent-panel-${tab.id}`}
            aria-selected={activeTab === tab.id}
            id={`agent-tab-${tab.id}`}
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
            {tab.id === "notifications" && unreadCount > 0 ? ` (${unreadCount})` : ""}
          </button>
        ))}
      </div>

      <div
        aria-labelledby="agent-tab-agents"
        className={styles.tabPanel}
        hidden={activeTab !== "agents"}
        id="agent-panel-agents"
        role="tabpanel"
        tabIndex={activeTab === "agents" ? 0 : -1}
      >
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
      </div>

      <div
        aria-labelledby="agent-tab-runs"
        className={styles.tabPanel}
        hidden={activeTab !== "runs"}
        id="agent-panel-runs"
        role="tabpanel"
        tabIndex={activeTab === "runs" ? 0 : -1}
      >
        <RunPanel onRunsChange={setRuns} runs={runs} />
      </div>

      <div
        aria-labelledby="agent-tab-rules"
        className={styles.tabPanel}
        hidden={activeTab !== "rules"}
        id="agent-panel-rules"
        role="tabpanel"
        tabIndex={activeTab === "rules" ? 0 : -1}
      >
        <RulePanel
          accounts={initial.accounts}
          agents={agents}
          onRulesChange={setRules}
          rules={rules}
        />
      </div>

      <div
        aria-labelledby="agent-tab-notifications"
        className={styles.tabPanel}
        hidden={activeTab !== "notifications"}
        id="agent-panel-notifications"
        role="tabpanel"
        tabIndex={activeTab === "notifications" ? 0 : -1}
      >
        <NotificationPanel
          notifications={notifications}
          onNotificationsChange={(items, unread) => {
            setNotifications(items);
            setUnreadCount(unread);
          }}
        />
      </div>
    </div>
  );
}
