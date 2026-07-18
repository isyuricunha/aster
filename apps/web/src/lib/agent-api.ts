import { apiRequest } from "./api";

export type AgentTriggerType =
  | "manual"
  | "once"
  | "interval"
  | "daily"
  | "weekly"
  | "communication";
export type AgentRunStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled";
export type AgentApprovalPolicy = "always" | "tool_default" | "never";

export type AgentToolScope = {
  id: string;
  tool_id: string;
  server_name: string;
  tool_name: string;
  public_name: string;
  approval_policy: AgentApprovalPolicy;
  requires_confirmation: boolean;
  is_available: boolean;
};

export type AgentCommunicationScope = {
  id: string;
  account_id: string;
  account_name: string;
  account_kind: "imap" | "discord";
  allow_read: boolean;
  allow_reply: boolean;
  reply_approval_policy: "always" | "never";
};

export type AgentKnowledgeScope = {
  id: string;
  collection_id: string;
  collection_name: string;
};

export type Agent = {
  id: string;
  name: string;
  description: string;
  goal: string;
  enabled: boolean;
  paused: boolean;
  trigger_type: AgentTriggerType;
  timezone: string;
  schedule: Record<string, unknown>;
  next_run_at: string | null;
  model_id: string | null;
  persona_id: string | null;
  persona_name: string | null;
  persona_description: string | null;
  persona_instruction_role: string | null;
  memory_enabled: boolean;
  rag_enabled: boolean;
  max_steps: number;
  max_model_calls: number;
  max_tool_calls: number;
  max_runtime_seconds: number;
  max_estimated_tokens: number;
  max_estimated_cost_microusd: number | null;
  input_cost_per_million_microusd: number | null;
  output_cost_per_million_microusd: number | null;
  notify_on_completion: boolean;
  notify_on_failure: boolean;
  tools: AgentToolScope[];
  communication_scopes: AgentCommunicationScope[];
  knowledge_scopes: AgentKnowledgeScope[];
  last_enqueued_at: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentWrite = {
  name: string;
  description: string;
  goal: string;
  enabled: boolean;
  paused: boolean;
  trigger_type: AgentTriggerType;
  timezone: string;
  schedule: Record<string, unknown>;
  model_id: string | null;
  persona_id: string | null;
  use_default_persona: boolean;
  memory_enabled: boolean;
  rag_enabled: boolean;
  max_steps: number;
  max_model_calls: number;
  max_tool_calls: number;
  max_runtime_seconds: number;
  max_estimated_tokens: number;
  max_estimated_cost_microusd: number | null;
  input_cost_per_million_microusd: number | null;
  output_cost_per_million_microusd: number | null;
  notify_on_completion: boolean;
  notify_on_failure: boolean;
  tools: Array<{ tool_id: string; approval_policy: AgentApprovalPolicy }>;
  communication_scopes: Array<{
    account_id: string;
    allow_read: boolean;
    allow_reply: boolean;
    reply_approval_policy: "always" | "never";
  }>;
  knowledge_scopes: Array<{ collection_id: string }>;
};

export type AgentStep = {
  id: string;
  run_id: string;
  position: number;
  kind: "system" | "model" | "plan" | "tool" | "communication" | "final";
  status: "running" | "waiting_approval" | "completed" | "failed" | "denied" | "skipped";
  summary: string;
  content: string | null;
  provider_model_id: string | null;
  tool_id: string | null;
  tool_call_id: string | null;
  tool_name: string | null;
  arguments: Record<string, unknown>;
  result: string | null;
  fingerprint: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentApproval = {
  id: string;
  run_id: string;
  step_id: string;
  action_type: "tool" | "communication_reply";
  status: "pending" | "approved" | "denied" | "cancelled";
  title: string;
  details: string;
  payload: Record<string, unknown>;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentRun = {
  id: string;
  agent_id: string;
  agent_name: string;
  trigger_source: "manual" | "schedule" | "communication" | "retry";
  status: AgentRunStatus;
  scheduled_for: string;
  available_at: string;
  lease_owner: string | null;
  lease_expires_at: string | null;
  goal_snapshot: string;
  trigger_payload: Record<string, unknown>;
  plan: Array<Record<string, unknown>>;
  persona_name: string | null;
  requested_model_id: string | null;
  provider_model_id: string | null;
  max_steps: number;
  max_model_calls: number;
  max_tool_calls: number;
  max_runtime_seconds: number;
  max_estimated_tokens: number;
  max_estimated_cost_microusd: number | null;
  steps_used: number;
  model_calls_used: number;
  tool_calls_used: number;
  estimated_tokens: number;
  estimated_cost_microusd: number;
  final_output: string | null;
  error_code: string | null;
  error_message: string | null;
  pause_requested: boolean;
  cancel_requested: boolean;
  deadline_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  steps: AgentStep[];
  approvals: AgentApproval[];
  created_at: string;
  updated_at: string;
};

export type AgentCommunicationRule = {
  id: string;
  name: string;
  agent_id: string;
  agent_name: string;
  account_id: string;
  account_name: string;
  enabled: boolean;
  sender_pattern: string | null;
  source_ids: string[];
  body_contains: string | null;
  require_mention: boolean;
  created_at: string;
  updated_at: string;
};

export type AgentCommunicationRuleWrite = Omit<
  AgentCommunicationRule,
  "id" | "agent_name" | "account_name" | "created_at" | "updated_at"
>;

export type AgentControl = {
  emergency_stop: boolean;
  reason: string;
  activated_at: string | null;
  updated_at: string;
};

export type AgentNotification = {
  id: string;
  agent_id: string | null;
  run_id: string | null;
  level: "info" | "success" | "error";
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentNotificationList = {
  items: AgentNotification[];
  unread_count: number;
  total: number;
};

export function listAgents(): Promise<Agent[]> {
  return apiRequest<Agent[]>("/api/agents");
}
export function createAgent(payload: AgentWrite): Promise<Agent> {
  return apiRequest<Agent>("/api/agents", { method: "POST", body: JSON.stringify(payload) });
}
export function updateAgent(id: string, payload: AgentWrite): Promise<Agent> {
  return apiRequest<Agent>(`/api/agents/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
export function deleteAgent(id: string): Promise<void> {
  return apiRequest<void>(`/api/agents/${id}`, { method: "DELETE" });
}
export function runAgent(id: string): Promise<AgentRun> {
  return apiRequest<AgentRun>(`/api/agents/${id}/run`, { method: "POST" });
}
export function listAgentRuns(): Promise<AgentRun[]> {
  return apiRequest<AgentRun[]>("/api/agent-runs?limit=100");
}
export function readAgentRun(id: string): Promise<AgentRun> {
  return apiRequest<AgentRun>(`/api/agent-runs/${id}`);
}
export function pauseAgentRun(id: string): Promise<{ status: AgentRunStatus; run_id: string }> {
  return apiRequest(`/api/agent-runs/${id}/pause`, { method: "POST" });
}
export function resumeAgentRun(id: string): Promise<{ status: AgentRunStatus; run_id: string }> {
  return apiRequest(`/api/agent-runs/${id}/resume`, { method: "POST" });
}
export function cancelAgentRun(id: string): Promise<{ status: AgentRunStatus; run_id: string }> {
  return apiRequest(`/api/agent-runs/${id}/cancel`, { method: "POST" });
}
export function retryAgentRun(id: string): Promise<AgentRun> {
  return apiRequest<AgentRun>(`/api/agent-runs/${id}/retry`, { method: "POST" });
}
export function approveAgentAction(id: string): Promise<AgentRun> {
  return apiRequest<AgentRun>(`/api/agent-approvals/${id}/approve`, { method: "POST" });
}
export function denyAgentAction(id: string): Promise<AgentRun> {
  return apiRequest<AgentRun>(`/api/agent-approvals/${id}/deny`, { method: "POST" });
}
export function getAgentControl(): Promise<AgentControl> {
  return apiRequest<AgentControl>("/api/agent-control");
}
export function setAgentControl(emergencyStop: boolean, reason: string): Promise<AgentControl> {
  return apiRequest<AgentControl>("/api/agent-control", {
    method: "PUT",
    body: JSON.stringify({ emergency_stop: emergencyStop, reason }),
  });
}
export function listAgentCommunicationRules(): Promise<AgentCommunicationRule[]> {
  return apiRequest<AgentCommunicationRule[]>("/api/agent-communication-rules");
}
export function createAgentCommunicationRule(
  payload: AgentCommunicationRuleWrite,
): Promise<AgentCommunicationRule> {
  return apiRequest<AgentCommunicationRule>("/api/agent-communication-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
export function updateAgentCommunicationRule(
  id: string,
  payload: AgentCommunicationRuleWrite,
): Promise<AgentCommunicationRule> {
  return apiRequest<AgentCommunicationRule>(`/api/agent-communication-rules/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
export function deleteAgentCommunicationRule(id: string): Promise<void> {
  return apiRequest<void>(`/api/agent-communication-rules/${id}`, { method: "DELETE" });
}
export function listAgentNotifications(): Promise<AgentNotificationList> {
  return apiRequest<AgentNotificationList>("/api/agent-notifications?limit=100");
}
export function markAgentNotificationRead(id: string): Promise<AgentNotification> {
  return apiRequest<AgentNotification>(`/api/agent-notifications/${id}/read`, {
    method: "POST",
  });
}
export function markAllAgentNotificationsRead(): Promise<void> {
  return apiRequest<void>("/api/agent-notifications/read-all", { method: "POST" });
}
export function deleteAgentNotification(id: string): Promise<void> {
  return apiRequest<void>(`/api/agent-notifications/${id}`, { method: "DELETE" });
}
