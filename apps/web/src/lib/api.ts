export type ModelEndpoint = {
  id: string;
  name: string;
  base_url: string;
  enabled: boolean;
  has_api_key: boolean;
  cached_model_count: number;
  last_sync_status: "running" | "succeeded" | "failed" | null;
  last_sync_at: string | null;
  last_successful_sync_at: string | null;
  last_sync_error: string | null;
  created_at: string;
  updated_at: string;
};

export type CachedModel = {
  id: string;
  endpoint_id: string;
  endpoint_name: string;
  model_id: string;
  is_manual: boolean;
  is_available: boolean;
  first_seen_at: string | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SelectedModel = {
  id: string;
  endpoint_id: string;
  endpoint_name: string;
  model_id: string;
  endpoint_enabled: boolean;
  is_available: boolean;
};

export type ModelPreferences = {
  primary: SelectedModel | null;
  utility: SelectedModel | null;
  image: SelectedModel | null;
  resolved_utility: SelectedModel | null;
};

export type ModelProfile = {
  model_id: string;
  endpoint_id: string;
  endpoint_name: string;
  provider_model_id: string;
  display_name: string | null;
  context_window: number | null;
  max_output_tokens: number | null;
  token_parameter: "none" | "max_tokens" | "max_completion_tokens";
  temperature: number | null;
  top_p: number | null;
  reasoning_effort: "minimal" | "low" | "medium" | "high" | "xhigh" | null;
  supports_chat: boolean;
  supports_streaming: boolean;
  endpoint_enabled: boolean;
  is_available: boolean;
  created_at: string | null;
  updated_at: string | null;
};

export type FallbackModel = {
  id: string;
  endpoint_id: string;
  endpoint_name: string;
  model_id: string;
  display_name: string | null;
  endpoint_enabled: boolean;
  is_available: boolean;
  supports_chat: boolean;
  supports_streaming: boolean;
};

export type ModelRouting = {
  fallbacks: FallbackModel[];
};

export type Persona = {
  id: string;
  name: string;
  description: string;
  instructions: string;
  enabled: boolean;
  instruction_role: "developer" | "system";
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type PersonaPreferences = {
  default_persona: Persona | null;
};

export type PersonaSettings = {
  name: string;
  instructions: string;
  enabled: boolean;
  instruction_role: "developer" | "system";
  created_at: string;
  updated_at: string;
};

export type PersonaTransfer = {
  format: "aster-persona";
  version: 1;
  name: string;
  description: string;
  instructions: string;
  enabled: boolean;
  instruction_role: "developer" | "system";
};

export type CanonicalMessage = {
  role: "system" | "developer" | "user" | "assistant" | "tool";
  source: "platform" | "persona" | "conversation" | "user" | "assistant" | "tool";
  content: string;
};

export type CompositionPreview = {
  messages: CanonicalMessage[];
};

export type ToolCall = {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string;
  };
};

export type ToolExecution = {
  id: string;
  conversation_id: string;
  assistant_message_id: string;
  tool_message_id: string | null;
  tool_id: string | null;
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  status: "pending_confirmation" | "running" | "completed" | "failed" | "denied";
  result: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  status: "completed" | "streaming" | "failed" | "stopped";
  error_message: string | null;
  model_id: string | null;
  tool_calls?: ToolCall[] | null;
  tool_call_id?: string | null;
  tool_name?: string | null;
  position: number;
  created_at: string;
  updated_at: string;
};

export type ConversationPersona = {
  source_persona_id: string | null;
  name: string;
  description: string;
  instructions: string;
  instruction_role: "developer" | "system";
};

export type ConversationSummary = {
  id: string;
  title: string;
  message_count: number;
  persona_name: string | null;
  created_at: string;
  updated_at: string;
};

export type Conversation = {
  id: string;
  title: string;
  persona?: ConversationPersona | null;
  messages: ChatMessage[];
  tool_executions?: ToolExecution[];
  created_at: string;
  updated_at: string;
};

export type ConversationTransferMessage = {
  role: "user" | "assistant" | "tool";
  content: string;
  status: "completed" | "failed" | "stopped";
  error_message: string | null;
  model_id: string | null;
  tool_calls?: ToolCall[] | null;
  tool_call_id?: string | null;
  tool_name?: string | null;
};

export type ConversationTransfer = {
  format: "aster-conversation";
  version: 1 | 2 | 3;
  title: string;
  persona?: ConversationPersona | null;
  messages: ConversationTransferMessage[];
};

export type McpServer = {
  id: string;
  name: string;
  transport: "streamable_http" | "stdio";
  url: string | null;
  command: string | null;
  arguments: string[];
  header_names: string[];
  environment_names: string[];
  enabled: boolean;
  timeout_seconds: number;
  tool_count: number;
  available_tool_count: number;
  last_sync_status: "succeeded" | "failed" | null;
  last_sync_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type McpTool = {
  id: string;
  server_id: string;
  server_name: string;
  name: string;
  public_name: string;
  description: string;
  input_schema: Record<string, unknown>;
  enabled: boolean;
  default_enabled: boolean;
  requires_confirmation: boolean;
  is_available: boolean;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationToolSettings = {
  conversation_id: string;
  tools: McpTool[];
};

export type AuthStatus = {
  setup_required: boolean;
  authenticated: boolean;
  username: string | null;
};

export type AuthUser = {
  username: string;
  created_at: string;
};

export type SessionRevocation = {
  revoked_sessions: number;
};

type ErrorPayload = {
  detail?: string | { message?: string };
};

export function apiUrl(path: string): string {
  return path;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers,
  });
  if (response.status === 204) {
    return undefined as T;
  }

  const payload = (await response.json().catch(() => null)) as T | ErrorPayload | null;

  if (!response.ok) {
    const detail = (payload as ErrorPayload | null)?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message ?? `Request failed with HTTP ${response.status}`;
    throw new Error(message);
  }

  return payload as T;
}
