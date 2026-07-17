import { apiRequest, apiUrl } from "./api";

export type ImageOutputFormat = "png" | "jpeg" | "webp";

export type MediaAsset = {
  id: string;
  source_type: "upload" | "generated" | "edited";
  original_filename: string | null;
  media_type: string;
  size_bytes: number;
  content_sha256: string;
  width: number;
  height: number;
  content_url: string;
  created_at: string;
  updated_at: string;
};

export type MessageAttachment = MediaAsset & {
  attachment_type: "input" | "output";
  position: number;
};

export type ImageModelProfile = {
  model_id: string;
  endpoint_id: string;
  endpoint_name: string;
  provider_model_id: string;
  supports_generation: boolean;
  supports_editing: boolean;
  supports_multiple_inputs: boolean;
  supports_masks: boolean;
  max_input_images: number;
  default_size: string | null;
  default_quality: string | null;
  default_output_format: ImageOutputFormat;
  default_background: string | null;
  default_count: number;
  default_input_fidelity: string | null;
  provider_parameters: Record<string, unknown>;
  endpoint_enabled: boolean;
  is_available: boolean;
  created_at: string | null;
  updated_at: string | null;
};

export type ImageOperation = {
  id: string;
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  operation_type: "generation" | "edit";
  status: "running" | "completed" | "failed";
  model_cache_entry_id: string | null;
  provider_model_id: string;
  prompt: string;
  revised_prompt: string | null;
  parameters: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  inputs: MessageAttachment[];
  outputs: MessageAttachment[];
  started_at: string;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ImageGallery = {
  items: ImageOperation[];
  total: number;
  offset: number;
  limit: number;
};

export type ImageOperationPayload = {
  prompt: string;
  input_asset_ids?: string[];
  mask_asset_id?: string | null;
  model_id?: string | null;
  size?: string | null;
  quality?: string | null;
  output_format?: ImageOutputFormat | null;
  background?: string | null;
  count?: number | null;
  input_fidelity?: string | null;
  provider_parameters?: Record<string, unknown>;
};

export async function uploadImageAsset(file: File): Promise<MediaAsset> {
  const response = await fetch(
    apiUrl(`/api/media-assets/uploads?filename=${encodeURIComponent(file.name)}`),
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    },
  );
  const payload = (await response.json().catch(() => null)) as
    | MediaAsset
    | { detail?: string | { message?: string } }
    | null;
  if (!response.ok) {
    const detail = payload && "detail" in payload ? payload.detail : null;
    throw new Error(
      typeof detail === "string"
        ? detail
        : detail?.message ?? `Upload failed with HTTP ${response.status}`,
    );
  }
  return payload as MediaAsset;
}

export function createImageOperation(
  conversationId: string,
  payload: ImageOperationPayload,
): Promise<ImageOperation> {
  return apiRequest<ImageOperation>(`/api/conversations/${conversationId}/image-operations`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listImageProfiles(): Promise<ImageModelProfile[]> {
  return apiRequest<ImageModelProfile[]>("/api/image-model-profiles");
}

export function updateImageProfile(
  modelId: string,
  profile: Omit<
    ImageModelProfile,
    | "model_id"
    | "endpoint_id"
    | "endpoint_name"
    | "provider_model_id"
    | "endpoint_enabled"
    | "is_available"
    | "created_at"
    | "updated_at"
  >,
): Promise<ImageModelProfile> {
  return apiRequest<ImageModelProfile>(`/api/image-model-profiles/${modelId}`, {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

export function formatBytes(value: number): string {
  if (value < 1_000) return `${value} B`;
  if (value < 1_000_000) return `${(value / 1_000).toFixed(1)} KB`;
  return `${(value / 1_000_000).toFixed(1)} MB`;
}
