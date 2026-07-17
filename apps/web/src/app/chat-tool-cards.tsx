import type { ToolCall, ToolExecution } from "../lib/api";
import { Icon } from "./ui/icons";
import styles from "./chat-tools.module.css";

export function ToolCallList({ calls }: { calls: ToolCall[] }) {
  if (!calls.length) return null;
  return (
    <div className={styles.callList}>
      {calls.map((call) => (
        <article className={styles.call} key={call.id}>
          <div className={styles.callHeader}>
            <span className={styles.icon}>
              <Icon name="tools" size={13} />
            </span>
            <div>
              <strong>Tool request</strong>
              <small>{call.function.name}</small>
            </div>
          </div>
          <pre>{formatArguments(call.function.arguments)}</pre>
        </article>
      ))}
    </div>
  );
}

export function ToolExecutionCard({
  execution,
  disabled,
  onDecision,
}: {
  execution: ToolExecution;
  disabled: boolean;
  onDecision: (execution: ToolExecution, decision: "approve" | "deny") => void;
}) {
  const pending = execution.status === "pending_confirmation";
  return (
    <article className={`${styles.execution} ${styles[execution.status]}`}>
      <div className={styles.executionHeader}>
        <div>
          <span className={styles.icon}>
            <Icon name="tools" size={13} />
          </span>
          <span>
            <strong>{execution.tool_name}</strong>
            <small>{statusLabel(execution.status)}</small>
          </span>
        </div>
        <code>{execution.tool_call_id}</code>
      </div>
      <pre>{JSON.stringify(execution.arguments, null, 2)}</pre>
      {execution.error_message ? <p className={styles.error}>{execution.error_message}</p> : null}
      {pending ? (
        <div className={styles.actions}>
          <button
            className="button secondary"
            disabled={disabled}
            onClick={() => onDecision(execution, "deny")}
            type="button"
          >
            Deny
          </button>
          <button
            className="button primary"
            disabled={disabled}
            onClick={() => onDecision(execution, "approve")}
            type="button"
          >
            Approve
          </button>
        </div>
      ) : null}
    </article>
  );
}

function statusLabel(status: ToolExecution["status"]): string {
  switch (status) {
    case "pending_confirmation":
      return "Waiting for approval";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "denied":
      return "Denied";
  }
}

function formatArguments(value: string): string {
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}
