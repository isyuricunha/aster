"use client";

import { useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { apiRequest, type CachedModel, type Persona } from "../../../lib/api";
import {
  saveMemory,
  uploadKnowledgeDocument,
  type KnowledgeCollection,
  type KnowledgeDocument,
  type Memory,
  type MemoryCategory,
  type RetrievalPreferences,
} from "../../../lib/retrieval-api";
import { Icon } from "../../ui/icons";
import {
  notifySettingsUpdated,
  SummaryCard,
  SummaryGrid,
  UnsavedBadge,
  useUnsavedChanges,
} from "../settings-primitives";
import styles from "../simple-settings.module.css";

type Tab = "memories" | "documents" | "collections" | "retrieval";

type MemoryDraft = {
  id?: string;
  content: string;
  category: MemoryCategory;
  persona_id: string | null;
  enabled: boolean;
};

type CollectionDraft = {
  id?: string;
  name: string;
  description: string;
  enabled: boolean;
  default_enabled: boolean;
};

const blankMemory: MemoryDraft = {
  content: "",
  category: "fact",
  persona_id: null,
  enabled: true,
};

const blankCollection: CollectionDraft = {
  name: "",
  description: "",
  enabled: true,
  default_enabled: false,
};

const categories: MemoryCategory[] = [
  "fact",
  "preference",
  "project",
  "relationship",
  "instruction",
  "other",
];

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function memoryDraft(memory: Memory): MemoryDraft {
  return {
    id: memory.id,
    content: memory.content,
    category: memory.category,
    persona_id: memory.persona_id,
    enabled: memory.enabled,
  };
}

function collectionDraft(collection: KnowledgeCollection): CollectionDraft {
  return {
    id: collection.id,
    name: collection.name,
    description: collection.description,
    enabled: collection.enabled,
    default_enabled: collection.default_enabled,
  };
}

function sameMemoryDraft(left: MemoryDraft, right: MemoryDraft): boolean {
  return (
    left.id === right.id &&
    left.content === right.content &&
    left.category === right.category &&
    left.persona_id === right.persona_id &&
    left.enabled === right.enabled
  );
}

function sameCollectionDraft(left: CollectionDraft, right: CollectionDraft): boolean {
  return (
    left.id === right.id &&
    left.name === right.name &&
    left.description === right.description &&
    left.enabled === right.enabled &&
    left.default_enabled === right.default_enabled
  );
}

export function SimpleMemorySettings({
  initialMemories,
  initialCollections,
  initialDocuments,
  initialPreferences,
  initialModels,
  initialPersonas,
  initialError,
}: {
  initialMemories: Memory[];
  initialCollections: KnowledgeCollection[];
  initialDocuments: KnowledgeDocument[];
  initialPreferences: RetrievalPreferences;
  initialModels: CachedModel[];
  initialPersonas: Persona[];
  initialError: string | null;
}) {
  const router = useRouter();
  const uploadRef = useRef<HTMLInputElement>(null);
  const [activeTab, setActiveTab] = useState<Tab>("memories");
  const [memories, setMemories] = useState(initialMemories);
  const [collections, setCollections] = useState(initialCollections);
  const [documents, setDocuments] = useState(initialDocuments);
  const [preferences, setPreferences] = useState(initialPreferences);
  const [memory, setMemory] = useState<MemoryDraft>(blankMemory);
  const [savedMemory, setSavedMemory] = useState<MemoryDraft>(blankMemory);
  const [collection, setCollection] = useState<CollectionDraft>(blankCollection);
  const [savedCollection, setSavedCollection] = useState<CollectionDraft>(blankCollection);
  const [uploadCollectionId, setUploadCollectionId] = useState(
    initialCollections.find((item) => item.enabled)?.id ?? "",
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);

  const memoryDirty = !sameMemoryDraft(memory, savedMemory);
  const collectionDirty = !sameCollectionDraft(collection, savedCollection);
  const enabledCollections = useMemo(
    () => collections.filter((item) => item.enabled),
    [collections],
  );
  const readyDocuments = documents.filter((item) => item.status === "ready").length;
  useUnsavedChanges(memoryDirty || collectionDirty);

  function completeUpdate(message: string) {
    setNotice(message);
    notifySettingsUpdated();
    router.refresh();
  }

  async function run(key: string, operation: () => Promise<void>) {
    if (busy) return;
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await operation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The operation failed.");
    } finally {
      setBusy(null);
    }
  }

  async function refreshMemories() {
    setMemories(await apiRequest<Memory[]>("/api/memories"));
  }

  async function refreshKnowledge() {
    const [nextCollections, nextDocuments] = await Promise.all([
      apiRequest<KnowledgeCollection[]>("/api/knowledge-collections"),
      apiRequest<KnowledgeDocument[]>("/api/knowledge-documents"),
    ]);
    setCollections(nextCollections);
    setDocuments(nextDocuments);
    if (!nextCollections.some((item) => item.id === uploadCollectionId && item.enabled)) {
      setUploadCollectionId(nextCollections.find((item) => item.enabled)?.id ?? "");
    }
  }

  async function saveMemoryDraft() {
    if (!memory.content.trim()) {
      setError("Memory content cannot be empty.");
      return;
    }
    await run("memory-save", async () => {
      await saveMemory({ ...memory, content: memory.content.trim() });
      await refreshMemories();
      setMemory(blankMemory);
      setSavedMemory(blankMemory);
      completeUpdate(memory.id ? "Memory updated." : "Memory saved.");
    });
  }

  async function removeMemory(item: Memory) {
    if (!window.confirm(`Delete this ${item.category} memory?`)) return;
    await run(`memory-delete:${item.id}`, async () => {
      await apiRequest<void>(`/api/memories/${item.id}`, { method: "DELETE" });
      await refreshMemories();
      if (memory.id === item.id) {
        setMemory(blankMemory);
        setSavedMemory(blankMemory);
      }
      completeUpdate("Memory deleted.");
    });
  }

  async function saveCollectionDraft() {
    if (!collection.name.trim()) {
      setError("Collection name cannot be empty.");
      return;
    }
    await run("collection-save", async () => {
      await apiRequest<KnowledgeCollection>(
        collection.id
          ? `/api/knowledge-collections/${collection.id}`
          : "/api/knowledge-collections",
        {
          method: collection.id ? "PUT" : "POST",
          body: JSON.stringify({
            name: collection.name.trim(),
            description: collection.description.trim(),
            enabled: collection.enabled,
            default_enabled: collection.enabled && collection.default_enabled,
          }),
        },
      );
      await refreshKnowledge();
      setCollection(blankCollection);
      setSavedCollection(blankCollection);
      completeUpdate(collection.id ? "Collection updated." : "Collection created.");
    });
  }

  async function removeCollection(item: KnowledgeCollection) {
    if (!window.confirm(`Delete ${item.name} and every indexed document inside it?`)) return;
    await run(`collection-delete:${item.id}`, async () => {
      await apiRequest<void>(`/api/knowledge-collections/${item.id}`, { method: "DELETE" });
      await refreshKnowledge();
      if (collection.id === item.id) {
        setCollection(blankCollection);
        setSavedCollection(blankCollection);
      }
      completeUpdate("Collection deleted.");
    });
  }

  async function uploadDocument(file: File) {
    if (!uploadCollectionId) {
      setError("Select a collection before uploading.");
      return;
    }
    await run("document-upload", async () => {
      await uploadKnowledgeDocument(uploadCollectionId, file);
      await refreshKnowledge();
      completeUpdate(`${file.name} was extracted and indexed.`);
    });
  }

  async function reindexDocument(item: KnowledgeDocument) {
    await run(`document-reindex:${item.id}`, async () => {
      await apiRequest<KnowledgeDocument>(`/api/knowledge-documents/${item.id}/reindex`, {
        method: "POST",
      });
      await refreshKnowledge();
      completeUpdate(`${item.filename} was reindexed.`);
    });
  }

  async function removeDocument(item: KnowledgeDocument) {
    if (!window.confirm(`Delete ${item.filename} from the private knowledge base?`)) return;
    await run(`document-delete:${item.id}`, async () => {
      await apiRequest<void>(`/api/knowledge-documents/${item.id}`, { method: "DELETE" });
      await refreshKnowledge();
      completeUpdate("Document deleted.");
    });
  }

  async function updateEmbeddingModel(modelId: string) {
    await run("embedding-model", async () => {
      const next = await apiRequest<RetrievalPreferences>("/api/retrieval-preferences", {
        method: "PUT",
        body: JSON.stringify({ embedding_model_id: modelId || null }),
      });
      setPreferences(next);
      completeUpdate(
        modelId
          ? "Embedding model selected. Existing content can be reindexed from Advanced settings."
          : "Embeddings disabled. Lexical retrieval remains available.",
      );
    });
  }

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: "memories", label: "Memories" },
    { id: "documents", label: "Documents" },
    { id: "collections", label: "Collections" },
    { id: "retrieval", label: "Retrieval" },
  ];

  return (
    <div aria-busy={busy !== null} className={styles.root}>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}
      {!error && notice ? <div className={styles.notice} role="status">{notice}</div> : null}

      <SummaryGrid>
        <SummaryCard
          label="Memories"
          value={String(memories.length)}
          note={`${memories.filter((item) => item.enabled).length} enabled`}
        />
        <SummaryCard
          label="Documents"
          value={`${readyDocuments}/${documents.length} ready`}
          note={`${documents.reduce((total, item) => total + item.chunk_count, 0)} chunks`}
        />
        <SummaryCard
          label="Collections"
          value={String(collections.length)}
          note={`${collections.filter((item) => item.default_enabled).length} new-chat defaults`}
        />
        <SummaryCard
          label="Retrieval"
          value={preferences.embedding_model ? "Hybrid" : "Lexical"}
          note={preferences.embedding_model?.model_id ?? "No embedding model"}
        />
      </SummaryGrid>

      <div aria-label="Memory and knowledge sections" className={styles.tabs} role="tablist">
        {tabs.map((tab) => (
          <button
            aria-selected={activeTab === tab.id}
            className={`${styles.tab} ${activeTab === tab.id ? styles.activeTab : ""}`}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "memories" ? (
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <h2>Approved memory</h2>
              <p>Only explicit approved items are available to retrieval.</p>
            </div>
            <UnsavedBadge visible={memoryDirty} />
          </div>
          <div className={styles.sectionBody}>
            <div className={styles.formGrid}>
              <label className={styles.wideField}>
                <span>Memory</span>
                <textarea
                  disabled={busy !== null}
                  maxLength={4000}
                  onChange={(event) => setMemory({ ...memory, content: event.target.value })}
                  placeholder="The user prefers direct technical answers."
                  rows={3}
                  value={memory.content}
                />
              </label>
              <label className={styles.field}>
                <span>Category</span>
                <select
                  disabled={busy !== null}
                  onChange={(event) =>
                    setMemory({ ...memory, category: event.target.value as MemoryCategory })
                  }
                  value={memory.category}
                >
                  {categories.map((category) => (
                    <option key={category} value={category}>{category}</option>
                  ))}
                </select>
              </label>
              <label className={styles.field}>
                <span>Scope</span>
                <select
                  disabled={busy !== null}
                  onChange={(event) =>
                    setMemory({ ...memory, persona_id: event.target.value || null })
                  }
                  value={memory.persona_id ?? ""}
                >
                  <option value="">Global</option>
                  {initialPersonas.map((persona) => (
                    <option key={persona.id} value={persona.id}>{persona.name}</option>
                  ))}
                </select>
              </label>
              <label className={styles.checkboxField}>
                <input
                  checked={memory.enabled}
                  disabled={busy !== null}
                  onChange={(event) => setMemory({ ...memory, enabled: event.target.checked })}
                  type="checkbox"
                />
                Enabled
              </label>
              <div className={styles.actions}>
                {memory.id || memoryDirty ? (
                  <button
                    className={styles.secondaryButton}
                    disabled={busy !== null}
                    onClick={() => {
                      setMemory(blankMemory);
                      setSavedMemory(blankMemory);
                    }}
                    type="button"
                  >
                    Cancel
                  </button>
                ) : null}
                <button
                  className={styles.primaryButton}
                  disabled={busy !== null || !memory.content.trim()}
                  onClick={() => void saveMemoryDraft()}
                  type="button"
                >
                  {busy === "memory-save" ? "Saving memory" : memory.id ? "Update memory" : "Save memory"}
                </button>
              </div>
            </div>

            <div className={styles.list}>
              {memories.length === 0 ? (
                <div className={styles.empty}>No approved memories yet.</div>
              ) : (
                memories.map((item) => (
                  <article className={styles.row} key={item.id}>
                    <div className={styles.rowMain}>
                      <div className={styles.badges}>
                        <span className={styles.badge}>{item.category}</span>
                        <span className={styles.badge}>{item.persona_name ?? "Global"}</span>
                        <span className={`${styles.badge} ${item.enabled ? styles.successBadge : styles.warningBadge}`}>
                          {item.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                      <p>{item.content}</p>
                    </div>
                    <div className={styles.rowActions}>
                      <button
                        className={styles.secondaryButton}
                        disabled={busy !== null}
                        onClick={() => {
                          const next = memoryDraft(item);
                          setMemory(next);
                          setSavedMemory(next);
                        }}
                        type="button"
                      >
                        Edit
                      </button>
                      <button
                        className={styles.dangerButton}
                        disabled={busy !== null}
                        onClick={() => void removeMemory(item)}
                        type="button"
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === "documents" ? (
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <h2>Private documents</h2>
              <p>Upload into an enabled collection. Extracted text stays behind authenticated routes.</p>
            </div>
          </div>
          <div className={styles.sectionBody}>
            <div className={styles.inlineControl}>
              <select
                aria-label="Collection for document upload"
                disabled={busy !== null}
                onChange={(event) => setUploadCollectionId(event.target.value)}
                value={uploadCollectionId}
              >
                <option value="">Select collection</option>
                {enabledCollections.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
              <button
                className={styles.primaryButton}
                disabled={!uploadCollectionId || busy !== null}
                onClick={() => uploadRef.current?.click()}
                type="button"
              >
                <Icon name="upload" size={14} /> Upload document
              </button>
              <input
                accept=".txt,.md,.markdown,.rst,.json,.jsonl,.csv,.tsv,.xml,.yaml,.yml,.toml,.ini,.log,.html,.htm,.pdf,text/*,application/pdf,application/json"
                className={styles.hiddenInput}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void uploadDocument(file);
                  event.target.value = "";
                }}
                ref={uploadRef}
                type="file"
              />
            </div>

            <div className={styles.list}>
              {documents.length === 0 ? (
                <div className={styles.empty}>No indexed documents.</div>
              ) : (
                documents.map((item) => (
                  <article className={styles.row} key={item.id}>
                    <div className={styles.rowMain}>
                      <div className={styles.badges}>
                        <span className={styles.badge}>{item.collection_name}</span>
                        <span
                          className={`${styles.badge} ${
                            item.status === "ready"
                              ? styles.successBadge
                              : item.status === "failed"
                                ? styles.dangerBadge
                                : styles.warningBadge
                          }`}
                        >
                          {item.status}
                        </span>
                        <span className={styles.badge}>
                          {item.embedded_chunk_count ? "Hybrid" : "Lexical"}
                        </span>
                      </div>
                      <strong>{item.filename}</strong>
                      <small>
                        {formatBytes(item.size_bytes)} · {item.chunk_count} chunks
                        {item.error_message ? ` · ${item.error_message}` : ""}
                      </small>
                    </div>
                    <div className={styles.rowActions}>
                      <button
                        className={styles.secondaryButton}
                        disabled={busy !== null}
                        onClick={() => void reindexDocument(item)}
                        type="button"
                      >
                        Reindex
                      </button>
                      <button
                        className={styles.dangerButton}
                        disabled={busy !== null}
                        onClick={() => void removeDocument(item)}
                        type="button"
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === "collections" ? (
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <h2>Knowledge collections</h2>
              <p>Group documents and decide which collections new conversations inherit.</p>
            </div>
            <UnsavedBadge visible={collectionDirty} />
          </div>
          <div className={styles.sectionBody}>
            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span>Name</span>
                <input
                  disabled={busy !== null}
                  maxLength={120}
                  onChange={(event) => setCollection({ ...collection, name: event.target.value })}
                  value={collection.name}
                />
              </label>
              <label className={styles.wideField}>
                <span>Description</span>
                <input
                  disabled={busy !== null}
                  maxLength={500}
                  onChange={(event) =>
                    setCollection({ ...collection, description: event.target.value })
                  }
                  value={collection.description}
                />
              </label>
              <label className={styles.checkboxField}>
                <input
                  checked={collection.enabled}
                  disabled={busy !== null}
                  onChange={(event) =>
                    setCollection({ ...collection, enabled: event.target.checked })
                  }
                  type="checkbox"
                />
                Enabled
              </label>
              <label className={styles.checkboxField}>
                <input
                  checked={collection.default_enabled}
                  disabled={busy !== null || !collection.enabled}
                  onChange={(event) =>
                    setCollection({ ...collection, default_enabled: event.target.checked })
                  }
                  type="checkbox"
                />
                Add to new conversations
              </label>
              <div className={styles.actions}>
                {collection.id || collectionDirty ? (
                  <button
                    className={styles.secondaryButton}
                    disabled={busy !== null}
                    onClick={() => {
                      setCollection(blankCollection);
                      setSavedCollection(blankCollection);
                    }}
                    type="button"
                  >
                    Cancel
                  </button>
                ) : null}
                <button
                  className={styles.primaryButton}
                  disabled={busy !== null || !collection.name.trim()}
                  onClick={() => void saveCollectionDraft()}
                  type="button"
                >
                  {busy === "collection-save"
                    ? "Saving collection"
                    : collection.id
                      ? "Update collection"
                      : "Create collection"}
                </button>
              </div>
            </div>

            <div className={styles.cardGrid}>
              {collections.length === 0 ? (
                <div className={styles.empty}>No knowledge collections yet.</div>
              ) : (
                collections.map((item) => (
                  <article className={styles.card} key={item.id}>
                    <div className={styles.badges}>
                      <span className={`${styles.badge} ${item.enabled ? styles.successBadge : styles.warningBadge}`}>
                        {item.enabled ? "Enabled" : "Disabled"}
                      </span>
                      {item.default_enabled ? (
                        <span className={`${styles.badge} ${styles.successBadge}`}>New chat default</span>
                      ) : null}
                    </div>
                    <div className={styles.cardMain}>
                      <strong>{item.name}</strong>
                      <p>{item.description || "No description."}</p>
                      <small>
                        {item.ready_document_count}/{item.document_count} ready · {item.chunk_count} chunks
                      </small>
                    </div>
                    <div className={styles.rowActions}>
                      <button
                        className={styles.secondaryButton}
                        disabled={busy !== null}
                        onClick={() => {
                          const next = collectionDraft(item);
                          setCollection(next);
                          setSavedCollection(next);
                        }}
                        type="button"
                      >
                        Edit
                      </button>
                      <button
                        className={styles.dangerButton}
                        disabled={busy !== null}
                        onClick={() => void removeCollection(item)}
                        type="button"
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>
        </section>
      ) : null}

      {activeTab === "retrieval" ? (
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div>
              <h2>Retrieval mode</h2>
              <p>Lexical search always works. An embedding model adds semantic similarity.</p>
            </div>
          </div>
          <div className={styles.sectionBody}>
            <label className={styles.field}>
              <span>Embedding model</span>
              <select
                disabled={busy !== null}
                onChange={(event) => void updateEmbeddingModel(event.target.value)}
                value={preferences.embedding_model?.id ?? ""}
              >
                <option value="">Lexical only</option>
                {initialModels.map((model) => (
                  <option disabled={!model.is_available} key={model.id} value={model.id}>
                    {model.endpoint_name} / {model.model_id}
                  </option>
                ))}
              </select>
            </label>
            <div className={styles.card}>
              <div className={styles.cardMain}>
                <strong>{preferences.embedding_model ? "Hybrid retrieval enabled" : "Lexical retrieval"}</strong>
                <p>
                  {preferences.embedding_model
                    ? "New and reindexed content can use both lexical and semantic scoring."
                    : "Memory and documents remain searchable without vector generation."}
                </p>
              </div>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
