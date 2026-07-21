import { apiRequest } from "./api";

export type IntegrationKind = "smtp" | "caldav" | "webhook";
export type TriggerType =
  | "once"
  | "interval"
  | "daily"
  | "weekly"
  | "webhook"
  | "communication";
export type DeliveryChannel = "email" | "calendar" | "webhook";
export type RunStatus =
  | "queued"
  | "running"
  | "delivering"
  | "completed"
  | "completed_with_errors"
  | "failed"
  | "cancelled";

export type IntegrationConnection = {
  id: string;
  name: string;
  kind: IntegrationKind;
  enabled: boolean;
  config: Record<string, unknown>;
  credential_names: string[];
  last_test_status: string | null;
  last_test_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type IntegrationWrite = {
  name: string;
  kind: IntegrationKind;
  enabled: boolean;
  config: Record<string, unknown>;
  credentials: Record<string, string>;
  preserve_credentials?: boolean;
};

export type AutomationDelivery = {
  id: string;
  integration_id: string;
  integration_name: string;
  channel: DeliveryChannel;
  enabled: boolean;
  config: Record<string, unknown>;
  position: number;
};

export type AutomationDeliveryWrite = {
  integration_id: string;
  channel: DeliveryChannel;
  enabled: boolean;
  config: Record<string, unknown>;
};

export type Automation = {
  id: string;
  builtin_key: string | null;
  state: Record<string, unknown>;
  name: string;
  description: string;
  instruction: string;
  enabled: boolean;
  trigger_type: TriggerType;
  timezone: string;
  schedule: Record<string, unknown>;
  next_run_at: string | null;
  model_id: string | null;
  persona_id: string | null;
  persona_name: string | null;
  persona_description: string | null;
  persona_instruction_role: "system" | "developer" | null;
  notify_on_success: boolean;
  notify_on_failure: boolean;
  max_attempts: number;
  retry_delay_seconds: number;
  timeout_seconds: number;
  webhook_configured: boolean;
  webhook_token: string | null;
  webhook_path: string | null;
  deliveries: AutomationDelivery[];
  last_enqueued_at: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AutomationWrite = {
  name: string;
  description: string;
  instruction: string;
  enabled: boolean;
  trigger_type: TriggerType;
  timezone: string;
  schedule: Record<string, unknown>;
  model_id: string | null;
  persona_id: string | null;
  use_default_persona: boolean;
  notify_on_success: boolean;
  notify_on_failure: boolean;
  max_attempts: number;
  retry_delay_seconds: number;
  timeout_seconds: number;
  deliveries: AutomationDeliveryWrite[];
};

export type DeliveryAttempt = {
  id: string;
  delivery_id: string | null;
  integration_id: string | null;
  channel: DeliveryChannel;
  status: "running" | "completed" | "failed";
  destination: string | null;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
};

export type AutomationRun = {
  id: string;
  automation_id: string;
  automation_name: string;
  trigger_source: "schedule" | "manual" | "webhook" | "communication" | "retry";
  status: RunStatus;
  scheduled_for: string;
  available_at: string;
  attempt: number;
  max_attempts: number;
  lease_owner: string | null;
  lease_expires_at: string | null;
  trigger_payload: Record<string, unknown>;
  instruction_snapshot: string;
  persona_name: string | null;
  provider_model_id: string | null;
  response: string | null;
  error_code: string | null;
  error_message: string | null;
  attempt_history: Array<Record<string, unknown>>;
  deliveries: DeliveryAttempt[];
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AutomationNotification = {
  id: string;
  automation_id: string | null;
  run_id: string | null;
  level: "info" | "success" | "error";
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
  updated_at: string;
};

export type NotificationList = {
  items: AutomationNotification[];
  unread_count: number;
  total: number;
};

export function listAutomations(): Promise<Automation[]> {
  return apiRequest<Automation[]>("/api/automations");
}

export function listTasks(): Promise<Automation[]> {
  return apiRequest<Automation[]>("/api/tasks");
}

export function createAutomation(payload: AutomationWrite): Promise<Automation> {
  return apiRequest<Automation>("/api/automations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAutomation(id: string, payload: AutomationWrite): Promise<Automation> {
  return apiRequest<Automation>(`/api/automations/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAutomation(id: string): Promise<void> {
  return apiRequest<void>(`/api/automations/${id}`, { method: "DELETE" });
}

export function setTaskEnabled(id: string, enabled: boolean): Promise<Automation> {
  return apiRequest<Automation>(`/api/tasks/${id}/enabled`, {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
}

export function runAutomation(id: string): Promise<AutomationRun> {
  return apiRequest<AutomationRun>(`/api/automations/${id}/run`, { method: "POST" });
}

export function runTask(id: string): Promise<AutomationRun> {
  return apiRequest<AutomationRun>(`/api/tasks/${id}/run`, { method: "POST" });
}

export function rotateWebhookToken(id: string): Promise<Automation> {
  return apiRequest<Automation>(`/api/automations/${id}/rotate-webhook-token`, {
    method: "POST",
  });
}

export function listAutomationRuns(): Promise<AutomationRun[]> {
  return apiRequest<AutomationRun[]>("/api/automation-runs?limit=100");
}

export function cancelAutomationRun(id: string): Promise<AutomationRun> {
  return apiRequest<AutomationRun>(`/api/automation-runs/${id}/cancel`, {
    method: "POST",
  });
}

export function retryAutomationRun(id: string): Promise<AutomationRun> {
  return apiRequest<AutomationRun>(`/api/automation-runs/${id}/retry`, {
    method: "POST",
  });
}

export function listIntegrations(): Promise<IntegrationConnection[]> {
  return apiRequest<IntegrationConnection[]>("/api/integrations");
}

export function createIntegration(payload: IntegrationWrite): Promise<IntegrationConnection> {
  return apiRequest<IntegrationConnection>("/api/integrations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateIntegration(
  id: string,
  payload: IntegrationWrite,
): Promise<IntegrationConnection> {
  return apiRequest<IntegrationConnection>(`/api/integrations/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteIntegration(id: string): Promise<void> {
  return apiRequest<void>(`/api/integrations/${id}`, { method: "DELETE" });
}

export function testIntegration(id: string): Promise<{ status: "ok"; message: string }> {
  return apiRequest<{ status: "ok"; message: string }>(`/api/integrations/${id}/test`, {
    method: "POST",
  });
}

export function listNotifications(): Promise<NotificationList> {
  return apiRequest<NotificationList>("/api/notifications?limit=100");
}

export function markNotificationRead(id: string): Promise<AutomationNotification> {
  return apiRequest<AutomationNotification>(`/api/notifications/${id}/read`, {
    method: "POST",
  });
}

export function markAllNotificationsRead(): Promise<void> {
  return apiRequest<void>("/api/notifications/read-all", { method: "POST" });
}

export function deleteNotification(id: string): Promise<void> {
  return apiRequest<void>(`/api/notifications/${id}`, { method: "DELETE" });
}
