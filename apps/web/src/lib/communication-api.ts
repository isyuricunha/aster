import { apiRequest } from "./api";

export type CommunicationKind = "imap" | "discord";
export type CommunicationThreadKind = "email" | "discord";

export type CommunicationAccount = {
  id: string;
  name: string;
  kind: CommunicationKind;
  enabled: boolean;
  config: Record<string, unknown>;
  credential_names: string[];
  external_identity: Record<string, unknown>;
  poll_interval_seconds: number;
  next_sync_at: string | null;
  last_sync_status: string | null;
  last_sync_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type CommunicationAccountWrite = {
  name: string;
  kind: CommunicationKind;
  enabled: boolean;
  config: Record<string, unknown>;
  credentials: Record<string, string>;
  poll_interval_seconds: number;
  preserve_credentials?: boolean;
};

export type CommunicationAttachment = {
  id: string;
  filename: string;
  media_type: string;
  size_bytes: number;
  sha256: string;
  content_path: string;
};

export type CommunicationMessage = {
  id: string;
  thread_id: string;
  account_id: string;
  external_message_id: string;
  direction: "inbound" | "outbound";
  source_id: string | null;
  sender_name: string | null;
  sender_address: string | null;
  recipients: Array<{ name: string; address: string }>;
  subject: string | null;
  content_text: string;
  content_html: string | null;
  metadata: Record<string, unknown>;
  is_read: boolean;
  sent_at: string;
  received_at: string;
  attachments: CommunicationAttachment[];
  created_at: string;
  updated_at: string;
};

export type CommunicationThread = {
  id: string;
  account_id: string;
  account_name: string;
  kind: CommunicationThreadKind;
  external_thread_id: string;
  title: string;
  participants: Array<{ name: string; address: string }>;
  metadata: Record<string, unknown>;
  unread_count: number;
  last_message_at: string;
  message_count: number;
  preview: string;
  created_at: string;
  updated_at: string;
};

export type CommunicationThreadDetail = CommunicationThread & {
  messages: CommunicationMessage[];
};

export type CommunicationRule = {
  id: string;
  name: string;
  account_id: string;
  account_name: string;
  automation_id: string;
  automation_name: string;
  enabled: boolean;
  sender_pattern: string | null;
  source_ids: string[];
  body_contains: string | null;
  require_mention: boolean;
  created_at: string;
  updated_at: string;
};

export type CommunicationRuleWrite = {
  name: string;
  account_id: string;
  automation_id: string;
  enabled: boolean;
  sender_pattern: string | null;
  source_ids: string[];
  body_contains: string | null;
  require_mention: boolean;
};

export function listCommunicationAccounts(): Promise<CommunicationAccount[]> {
  return apiRequest<CommunicationAccount[]>("/api/communication-accounts");
}

export function createCommunicationAccount(
  payload: CommunicationAccountWrite,
): Promise<CommunicationAccount> {
  return apiRequest<CommunicationAccount>("/api/communication-accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCommunicationAccount(
  id: string,
  payload: CommunicationAccountWrite,
): Promise<CommunicationAccount> {
  return apiRequest<CommunicationAccount>(`/api/communication-accounts/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteCommunicationAccount(id: string): Promise<void> {
  return apiRequest<void>(`/api/communication-accounts/${id}`, { method: "DELETE" });
}

export function testCommunicationAccount(
  id: string,
): Promise<{ status: "ok"; message: string; identity: Record<string, unknown> }> {
  return apiRequest(`/api/communication-accounts/${id}/test`, { method: "POST" });
}

export function syncCommunicationAccount(
  id: string,
): Promise<{ status: "ok"; messages_added: number; automations_enqueued: number }> {
  return apiRequest(`/api/communication-accounts/${id}/sync`, { method: "POST" });
}

export function listCommunicationThreads(params: {
  accountId?: string;
  kind?: CommunicationThreadKind | "";
  unreadOnly?: boolean;
  query?: string;
} = {}): Promise<CommunicationThread[]> {
  const query = new URLSearchParams();
  if (params.accountId) query.set("account_id", params.accountId);
  if (params.kind) query.set("kind", params.kind);
  if (params.unreadOnly) query.set("unread_only", "true");
  if (params.query?.trim()) query.set("query", params.query.trim());
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiRequest<CommunicationThread[]>(`/api/communication-threads${suffix}`);
}

export function readCommunicationThread(id: string): Promise<CommunicationThreadDetail> {
  return apiRequest<CommunicationThreadDetail>(`/api/communication-threads/${id}`);
}

export function markCommunicationThreadRead(id: string): Promise<CommunicationThreadDetail> {
  return apiRequest<CommunicationThreadDetail>(`/api/communication-threads/${id}/read`, {
    method: "POST",
  });
}

export function replyToCommunicationThread(
  id: string,
  content: string,
): Promise<CommunicationMessage> {
  return apiRequest<CommunicationMessage>(`/api/communication-threads/${id}/reply`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function listCommunicationRules(): Promise<CommunicationRule[]> {
  return apiRequest<CommunicationRule[]>("/api/communication-rules");
}

export function createCommunicationRule(
  payload: CommunicationRuleWrite,
): Promise<CommunicationRule> {
  return apiRequest<CommunicationRule>("/api/communication-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCommunicationRule(
  id: string,
  payload: CommunicationRuleWrite,
): Promise<CommunicationRule> {
  return apiRequest<CommunicationRule>(`/api/communication-rules/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteCommunicationRule(id: string): Promise<void> {
  return apiRequest<void>(`/api/communication-rules/${id}`, { method: "DELETE" });
}
