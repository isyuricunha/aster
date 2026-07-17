import { apiRequest, apiUrl, type SelectedModel } from "./api";

export type MemoryCategory =
  | "fact"
  | "preference"
  | "project"
  | "relationship"
  | "instruction"
  | "other";

export type Memory = {
  id: string;
  content: string;
  category: MemoryCategory;
  persona_id: string | null;
  persona_name: string | null;
  enabled: boolean;
  source_type: "manual" | "suggested" | "imported";
  source_conversation_id: string | null;
  has_embedding: boolean;
  created_at: string;
  updated_at: string;
};

export type MemorySuggestion = {
  id: string;
  conversation_id: string;
  persona_id: string | null;
  content: string;
  category: MemoryCategory;
  status: "pending" | "accepted" | "rejected";
  created_at: string;
  resolved_at: string | null;
};

export type MemoryTransfer = {
  format: "aster-memories";
  version: 1;
  memories: Array<{
    content: string;
    category: MemoryCategory;
    persona_name: string | null;
    enabled: boolean;
  }>;
};

export type RetrievalPreferences = {
  embedding_model: SelectedModel | null;
};

export type KnowledgeCollection = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  default_enabled: boolean;
  document_count: number;
  ready_document_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

export type KnowledgeDocument = {
  id: string;
  collection_id: string;
  collection_name: string;
  filename: string;
  media_type: string;
  size_bytes: number;
  content_sha256: string;
  status: "processing" | "ready" | "failed";
  error_message: string | null;
  chunk_count: number;
  embedded_chunk_count: number;
  embedding_model_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationRetrieval = {
  memory_enabled: boolean;
  rag_enabled: boolean;
  collection_ids: string[];
  collection_names: string[];
};

export type ConversationRetrievalSettings = {
  conversation_id: string;
  memory_enabled: boolean;
  rag_enabled: boolean;
  collections: KnowledgeCollection[];
};

export type RetrievalSource = {
  id: string;
  kind: "memory" | "document";
  rank: number;
  score: number | null;
  label: string;
  content: string;
  memory_id: string | null;
  chunk_id: string | null;
};

export async function uploadKnowledgeDocument(
  collectionId: string,
  file: File,
): Promise<KnowledgeDocument> {
  const response = await fetch(
    apiUrl(
      `/api/knowledge-collections/${collectionId}/documents?filename=${encodeURIComponent(file.name)}`,
    ),
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    },
  );
  const payload = (await response.json().catch(() => null)) as
    | KnowledgeDocument
    | { detail?: string | { message?: string } }
    | null;
  if (!response.ok) {
    const detail = payload && "detail" in payload ? payload.detail : undefined;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message ?? `Upload failed with HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload as KnowledgeDocument;
}

export function saveMemory(payload: {
  id?: string;
  content: string;
  category: MemoryCategory;
  persona_id: string | null;
  enabled: boolean;
}): Promise<Memory> {
  return apiRequest<Memory>(payload.id ? `/api/memories/${payload.id}` : "/api/memories", {
    method: payload.id ? "PUT" : "POST",
    body: JSON.stringify({
      content: payload.content,
      category: payload.category,
      persona_id: payload.persona_id,
      enabled: payload.enabled,
    }),
  });
}
