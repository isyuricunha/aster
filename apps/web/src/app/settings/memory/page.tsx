import type { Metadata } from "next";

import type {
  CachedModel,
  ConversationSummary,
  Persona,
} from "../../../lib/api";
import type {
  KnowledgeCollection,
  KnowledgeDocument,
  Memory,
  MemorySuggestion,
  RetrievalPreferences,
} from "../../../lib/retrieval-api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { AdvancedSettings } from "../settings-primitives";
import { MemorySettings } from "./memory-settings";
import { SimpleMemorySettings } from "./simple-memory-settings";

export const metadata: Metadata = { title: "Memory settings" };

export const dynamic = "force-dynamic";

type InitialMemorySettings = {
  memories: Memory[];
  suggestions: MemorySuggestion[];
  collections: KnowledgeCollection[];
  documents: KnowledgeDocument[];
  preferences: RetrievalPreferences;
  models: CachedModel[];
  personas: Persona[];
  conversations: ConversationSummary[];
  error: string | null;
};

type SettingsPageSearchParams = Promise<{ embedded?: string | string[] }>;

async function getInitialMemorySettings(): Promise<InitialMemorySettings> {
  try {
    const responses = await Promise.all([
      serverApiFetch("/api/memories"),
      serverApiFetch("/api/memory-suggestions?status_filter=pending"),
      serverApiFetch("/api/knowledge-collections"),
      serverApiFetch("/api/knowledge-documents"),
      serverApiFetch("/api/retrieval-preferences"),
      serverApiFetch("/api/models"),
      serverApiFetch("/api/personas"),
      serverApiFetch("/api/conversations"),
    ]);
    if (responses.some((response) => !response.ok)) {
      throw new Error("The memory and retrieval API returned an error.");
    }
    const [
      memories,
      suggestions,
      collections,
      documents,
      preferences,
      models,
      personas,
      conversations,
    ] = await Promise.all(responses.map((response) => response.json()));
    return {
      memories: memories as Memory[],
      suggestions: suggestions as MemorySuggestion[],
      collections: collections as KnowledgeCollection[],
      documents: documents as KnowledgeDocument[],
      preferences: preferences as RetrievalPreferences,
      models: models as CachedModel[],
      personas: personas as Persona[],
      conversations: conversations as ConversationSummary[],
      error: null,
    };
  } catch (error) {
    return {
      memories: [],
      suggestions: [],
      collections: [],
      documents: [],
      preferences: { embedding_model: null },
      models: [],
      personas: [],
      conversations: [],
      error: error instanceof Error ? error.message : "Could not load memory settings.",
    };
  }
}

export default async function MemorySettingsPage({
  searchParams,
}: {
  searchParams: SettingsPageSearchParams;
}) {
  await requireServerAuth();
  const [initialData, params] = await Promise.all([getInitialMemorySettings(), searchParams]);

  return (
    <AppFrame
      active="memory"
      kicker="Context"
      title="Memory & Knowledge"
      description="Manage approved memory and private documents through focused sections. Maintenance and per-chat overrides stay advanced."
      embedded={params.embedded === "1"}
    >
      <SimpleMemorySettings
        initialCollections={initialData.collections}
        initialDocuments={initialData.documents}
        initialError={initialData.error}
        initialMemories={initialData.memories}
        initialModels={initialData.models}
        initialPersonas={initialData.personas}
        initialPreferences={initialData.preferences}
      />
      <AdvancedSettings
        description="Memory suggestions, import and export, bulk reindexing, embedding maintenance, and per-conversation retrieval scope."
      >
        <MemorySettings
          initialMemories={initialData.memories}
          initialSuggestions={initialData.suggestions}
          initialCollections={initialData.collections}
          initialDocuments={initialData.documents}
          initialPreferences={initialData.preferences}
          initialModels={initialData.models}
          initialPersonas={initialData.personas}
          initialConversations={initialData.conversations}
          initialError={initialData.error}
        />
      </AdvancedSettings>
    </AppFrame>
  );
}
