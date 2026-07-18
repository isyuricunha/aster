"use client";

import { useMemo, useState } from "react";

import {
  approveAgentAction,
  cancelAgentRun,
  denyAgentAction,
  listAgentRuns,
  pauseAgentRun,
  resumeAgentRun,
  retryAgentRun,
  type AgentRun,
} from "../../lib/agent-api";
import styles from "./agents.module.css";

function formatDate(value: string | null): string {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatCost(microusd: number): string {
  return `$${(microusd / 1_000_000).toFixed(6)}`;
}

export function RunPanel({
  runs,
  onRunsChange,
}: {
  runs: AgentRun[];
  onRunsChange: (runs: AgentRun[]) => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(runs[0]?.id ?? null);
  const [working, setWorking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const selected = useMemo(
    () => runs.find((item) => item.id === selectedId) ?? runs[0] ?? null,
    [runs, selectedId],
  );

  async function refresh(preferredId?: string) {
    const next = await listAgentRuns();
    onRunsChange(next);
    const target = preferredId ?? selectedId;
    if (target && next.some((item) => item.id === target)) setSelectedId(target);
    else setSelectedId(next[0]?.id ?? null);
  }

  async function refreshRuns() {
    if (working) return;
    setWorking("refresh");
    setError(null);
    setMessage(null);
    try {
      await refresh();
      setMessage("Agent runs refreshed.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not refresh agent runs.");
    } finally {
      setWorking(null);
    }
  }

  async function act(action: "pause" | "resume" | "cancel" | "retry") {
    if (!selected || working) return;
    if (
      action === "cancel" &&
      !window.confirm(`Cancel the run for "${selected.agent_name}"? The current run cannot be resumed.`)
    ) {
      return;
    }
    setWorking(action);
    setError(null);
    setMessage(null);
    try {
      if (action === "pause") await pauseAgentRun(selected.id);
      else if (action === "resume") await resumeAgentRun(selected.id);
      else if (action === "cancel") await cancelAgentRun(selected.id);
      else {
        const retry = await retryAgentRun(selected.id);
        await refresh(retry.id);
        setMessage("A retry was queued from the saved run snapshot.");
        return;
      }
      await refresh(selected.id);
      setMessage(
        action === "pause"
          ? "Run paused."
          : action === "resume"
            ? "Run resumed."
            : "Run cancelled.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not ${action} the run.`);
    } finally {
      setWorking(null);
    }
  }

  async function decide(approvalId: string, decision: "approve" | "deny") {
    if (working) return;
    setWorking(`${decision}-${approvalId}`);
    setError(null);
    setMessage(null);
    try {
      const updated =
        decision === "approve"
          ? await approveAgentAction(approvalId)
          : await denyAgentAction(approvalId);
      await refresh(updated.id);
      setMessage(decision === "approve" ? "Action approved." : "Action denied.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not decide the action.");
    } finally {
      setWorking(null);
    }
  }

  return (
    <div className={styles.layout}>
      <aside aria-label="Agent runs" className={styles.sideList}>
        <button disabled={Boolean(working)} onClick={() => void refreshRuns()} type="button">
          {working === "refresh" ? "Refreshing runs…" : "Refresh runs"}
        </button>
        {runs.length === 0 ? (
          <p className={styles.sideListEmpty} role="status">No autonomous agent runs yet.</p>
        ) : null}
        {runs.map((run) => (
          <button
            aria-pressed={selected?.id === run.id}
            data-selected={selected?.id === run.id}
            disabled={Boolean(working)}
            key={run.id}
            onClick={() => setSelectedId(run.id)}
            type="button"
          >
            <strong>{run.agent_name}</strong>
            <span className={styles.itemMeta}>{run.status} · {formatDate(run.created_at)}</span>
          </button>
        ))}
      </aside>

      <section aria-busy={Boolean(working)} aria-label="Run details" className={styles.panel}>
        {error ? <div className={styles.error} role="alert">{error}</div> : null}
        {message ? <div className={styles.success} role="status">{message}</div> : null}
        {!selected ? (
          <div className={styles.empty} role="status">No autonomous agent runs yet.</div>
        ) : (
          <>
            <header className={styles.panelHeader}>
              <div>
                <p>Run detail</p>
                <h2>{selected.agent_name}</h2>
                <span className={styles.status} data-status={selected.status} role="status">{selected.status}</span>
              </div>
              <div className={styles.headerActions}>
                {selected.status === "queued" || selected.status === "running" ? <button disabled={Boolean(working)} onClick={() => void act("pause")} type="button">{working === "pause" ? "Pausing run…" : "Pause run"}</button> : null}
                {selected.status === "paused" ? <button disabled={Boolean(working)} onClick={() => void act("resume")} type="button">{working === "resume" ? "Resuming run…" : "Resume run"}</button> : null}
                {!(["completed", "failed", "cancelled"] as string[]).includes(selected.status) ? <button className={styles.danger} disabled={Boolean(working)} onClick={() => void act("cancel")} type="button">{working === "cancel" ? "Cancelling run…" : "Cancel run"}</button> : null}
                {selected.status === "failed" || selected.status === "cancelled" ? <button disabled={Boolean(working)} onClick={() => void act("retry")} type="button">{working === "retry" ? "Queueing retry…" : "Retry run"}</button> : null}
                <button disabled={Boolean(working)} onClick={() => void refreshRuns()} type="button">{working === "refresh" ? "Refreshing run…" : "Refresh run"}</button>
              </div>
            </header>

            <div className={styles.metrics}>
              <Metric label="Trigger" value={selected.trigger_source} />
              <Metric label="Model" value={selected.provider_model_id ?? "Not started"} />
              <Metric label="Persona" value={selected.persona_name ?? "None"} />
              <Metric label="Steps" value={`${selected.steps_used}/${selected.max_steps}`} />
              <Metric label="Model calls" value={`${selected.model_calls_used}/${selected.max_model_calls}`} />
              <Metric label="Actions" value={`${selected.tool_calls_used}/${selected.max_tool_calls}`} />
              <Metric label="Estimated tokens" value={`${selected.estimated_tokens}/${selected.max_estimated_tokens}`} />
              <Metric label="Estimated cost" value={formatCost(selected.estimated_cost_microusd)} />
              <Metric label="Runtime deadline" value={formatDate(selected.deadline_at)} />
            </div>

            {selected.approvals.filter((item) => item.status === "pending").length ? (
              <section className={styles.section}>
                <div className={styles.sectionTitle}><p>Approval queue</p><h3>External actions waiting for the owner</h3></div>
                <div className={styles.cardList}>
                  {selected.approvals.filter((item) => item.status === "pending").map((approval) => (
                    <article className={styles.card} key={approval.id}>
                      <div className={styles.cardHeader}>
                        <div><strong>{approval.title}</strong><div className={styles.itemMeta}>{approval.action_type}</div></div>
                        <span className={styles.status} data-status="waiting_approval">pending</span>
                      </div>
                      <pre className={styles.pre}>{approval.details}</pre>
                      <div className={styles.approvalActions}>
                        <button aria-label={`Approve ${approval.title}`} className={styles.primary} disabled={Boolean(working)} onClick={() => void decide(approval.id, "approve")} type="button">{working === `approve-${approval.id}` ? "Approving…" : "Approve action"}</button>
                        <button aria-label={`Deny ${approval.title}`} className={styles.danger} disabled={Boolean(working)} onClick={() => void decide(approval.id, "deny")} type="button">{working === `deny-${approval.id}` ? "Denying…" : "Deny action"}</button>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            <section className={styles.section}>
              <div className={styles.sectionTitle}><p>Saved goal</p><h3>Immutable run snapshot</h3></div>
              <div className={styles.output}>{selected.goal_snapshot}</div>
            </section>

            {selected.plan.length ? (
              <section className={styles.section}>
                <div className={styles.sectionTitle}><p>Plan</p><h3>Persisted subtasks</h3></div>
                <pre className={styles.pre}>{JSON.stringify(selected.plan, null, 2)}</pre>
              </section>
            ) : null}

            <section className={styles.section}>
              <div className={styles.sectionTitle}><p>Timeline</p><h3>Every model decision and action</h3></div>
              <div className={styles.timeline}>
                {selected.steps.length === 0 ? <div className={styles.empty} role="status">The worker has not started this run.</div> : selected.steps.map((step) => (
                  <article key={step.id}>
                    <div className={styles.timelineHeader}>
                      <div><strong>#{step.position} · {step.summary}</strong><div className={styles.itemMeta}>{step.kind} · {formatDate(step.started_at)}</div></div>
                      <span className={styles.status} data-status={step.status}>{step.status}</span>
                    </div>
                    {step.content ? <div className={styles.output}>{step.content}</div> : null}
                    {step.tool_name ? <pre className={styles.pre}>{step.tool_name}\n{JSON.stringify(step.arguments, null, 2)}</pre> : null}
                    {step.result ? <pre className={styles.pre}>{step.result}</pre> : null}
                  </article>
                ))}
              </div>
            </section>

            <section className={styles.section}>
              <div className={styles.sectionTitle}><p>Outcome</p><h3>Final result or failure</h3></div>
              <div className={styles.output}>{selected.final_output || selected.error_message || "No final output yet."}</div>
            </section>
          </>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className={styles.metric}><span>{label}</span><strong>{value}</strong></div>;
}
