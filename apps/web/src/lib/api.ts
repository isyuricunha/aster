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

type ErrorPayload = {
  detail?: string | { message?: string };
};

const apiBaseUrl = process.env.NEXT_PUBLIC_ASTER_API_URL ?? "http://localhost:8000";

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
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

export type PersonaSettings = {
  name: string;
  instructions: string;
  enabled: boolean;
  instruction_role: "developer" | "system";
  created_at: string;
  updated_at: string;
};

export type CanonicalMessage = {
  role: "system" | "developer" | "user" | "assistant" | "tool";
  source: "platform" | "persona" | "conversation" | "user" | "assistant" | "tool";
  content: string;
};

export type CompositionPreview = {
  messages: CanonicalMessage[];
};
