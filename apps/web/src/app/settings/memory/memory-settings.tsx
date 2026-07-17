"use client";

import { useRef, useState } from "react";

import {
  apiRequest,
  type CachedModel,
  type ConversationSummary,
  type Persona,
} from "../../../lib/api";
import {
  type ConversationRetrievalSettings,
  type KnowledgeCollection,
  type KnowledgeDocument,
  type Memory,
  type MemoryCategory,
  type MemorySuggestion,
  type MemoryTransfer,
  type RetrievalPreferences,
  saveMemory,
  uploadKnowledgeDocument,
} from "../../../lib/retrieval-api";
import { Icon } from "../../ui/icons";
import styles from "./memory.module.css";

type Props = {
  initialMemories: Memory[];
  initialSuggestions: MemorySuggestion[];
  initialCollections: KnowledgeCollection[];
  initialDocuments: KnowledgeDocument[];
  initialPreferences: RetrievalPreferences;
  initialModels: CachedModel[];
  initialPersonas: Persona[];
  initialConversations: ConversationSummary[];
  initialError: string | null;
};

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

function downloadJson(filename: string, value: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function MemorySettings({
  initialMemories,
  initialSuggestions,
  initialCollections,
  initialDocuments,
  initialPreferences,
  initialModels,
  initialPersonas,
  initialConversations,
  initialError,
}: Props) {
  const [memories, setMemories] = useState(initialMemories);
  const [suggestions, setSuggestions] = useState(initialSuggestions);
  const [collections, setCollections] = useState(initialCollections);
  const [documents, setDocuments] = useState(initialDocuments);
  const [preferences, setPreferences] = useState(initialPreferences);
  const [memoryDraft, setMemoryDraft] = useState<MemoryDraft>(blankMemory);
  const [collectionDraft, setCollectionDraft] = useState<CollectionDraft>(blankCollection);
  const [suggestionConversationId, setSuggestionConversationId] = useState(
    initialConversations[0]?.id ?? "",
  );
  const [scopeConversationId, setScopeConversationId] = useState(
    initialConversations[0]?.id ?? "",
  );
  const [scope, setScope] = useState<ConversationRetrievalSettings | null>(null);
  const [uploadCollectionId, setUploadCollectionId] = useState(
    initialCollections[0]?.id ?? "",
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState(initialError);
  const [notice, setNotice] = useState<string | null>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const uploadRef = useRef<HTMLInputElement>(null);

  async function run(key: string, action: () => Promise<void>) {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The request failed.");
    } finally {
      setBusy(null);
    }
  }

  async function refreshMemories() {
    setMemories(await apiRequest<Memory[]>("/api/memories"));
  }

  async function refreshSuggestions() {
    setSuggestions(
      await apiRequest<MemorySuggestion[]>(
        "/api/memory-suggestions?status_filter=pending",
      ),
    );
  }

  async function refreshKnowledge() {
    const [nextCollections, nextDocuments] = await Promise.all([
      apiRequest<KnowledgeCollection[]>("/api/knowledge-collections"),
      apiRequest<KnowledgeDocument[]>("/api/knowledge-documents"),
    ]);
    setCollections(nextCollections);
    setDocuments(nextDocuments);
    if (!uploadCollectionId && nextCollections[0]) {
      setUploadCollectionId(nextCollections[0].id);
    }
  }

  async function saveMemoryDraft() {
    await run("memory-save", async () => {
      if (!memoryDraft.content.trim()) throw new Error("Memory content cannot be empty.");
      await saveMemory(memoryDraft);
      await refreshMemories();
      setMemoryDraft(blankMemory);
      setNotice(memoryDraft.id ? "Memory updated." : "Memory saved.");
    });
  }

  async function removeMemory(memory: Memory) {
    if (!window.confirm(`Delete this ${memory.category} memory?`)) return;
    await run(`memory-delete-${memory.id}`, async () => {
      await apiRequest<void>(`/api/memories/${memory.id}`, { method: "DELETE" });
      await refreshMemories();
      if (memoryDraft.id === memory.id) setMemoryDraft(blankMemory);
    });
  }

  async function exportMemories() {
    await run("memory-export", async () => {
      const payload = await apiRequest<MemoryTransfer>("/api/memories/export");
      downloadJson("aster-memories.json", payload);
    });
  }

  async function importMemories(file: File) {
    await run("memory-import", async () => {
      const payload = JSON.parse(await file.text()) as MemoryTransfer;
      await apiRequest<Memory[]>("/api/memories/import", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await refreshMemories();
      setNotice("Memory import completed.");
    });
  }

  async function updateEmbeddingModel(modelId: string) {
    await run("embedding-model", async () => {
      const next = await apiRequest<RetrievalPreferences>("/api/retrieval-preferences", {
        method: "PUT",
        body: JSON.stringify({ embedding_model_id: modelId || null }),
      });
      setPreferences(next);
      setNotice(
        modelId
          ? "Embedding model selected. Reindex existing content to generate vectors."
          : "Embeddings disabled. Lexical retrieval remains available.",
      );
    });
  }

  async function reindexMemories() {
    await run("memory-reindex", async () => {
      setMemories(await apiRequest<Memory[]>("/api/memories/reindex", { method: "POST" }));
      setNotice("Memory reindex completed.");
    });
  }

  async function generateSuggestions() {
    if (!suggestionConversationId) return;
    await run("suggest-generate", async () => {
      await apiRequest<MemorySuggestion[]>(
        `/api/conversations/${suggestionConversationId}/memory-suggestions/generate`,
        { method: "POST" },
      );
      await refreshSuggestions();
    });
  }

  async function acceptSuggestion(suggestion: MemorySuggestion) {
    await run(`suggest-accept-${suggestion.id}`, async () => {
      await apiRequest<Memory>(`/api/memory-suggestions/${suggestion.id}/accept`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await Promise.all([refreshSuggestions(), refreshMemories()]);
    });
  }

  async function rejectSuggestion(suggestion: MemorySuggestion) {
    await run(`suggest-reject-${suggestion.id}`, async () => {
      await apiRequest(`/api/memory-suggestions/${suggestion.id}/reject`, {
        method: "POST",
      });
      await refreshSuggestions();
    });
  }

  async function saveCollectionDraft() {
    await run("collection-save", async () => {
      if (!collectionDraft.name.trim()) throw new Error("Collection name cannot be empty.");
      await apiRequest<KnowledgeCollection>(
        collectionDraft.id
          ? `/api/knowledge-collections/${collectionDraft.id}`
          : "/api/knowledge-collections",
        {
          method: collectionDraft.id ? "PUT" : "POST",
          body: JSON.stringify({
            name: collectionDraft.name,
            description: collectionDraft.description,
            enabled: collectionDraft.enabled,
            default_enabled: collectionDraft.enabled && collectionDraft.default_enabled,
          }),
        },
      );
      await refreshKnowledge();
      setCollectionDraft(blankCollection);
    });
  }

  async function removeCollection(collection: KnowledgeCollection) {
    if (!window.confirm(`Delete ${collection.name} and every indexed document inside it?`)) return;
    await run(`collection-delete-${collection.id}`, async () => {
      await apiRequest<void>(`/api/knowledge-collections/${collection.id}`, {
        method: "DELETE",
      });
      await refreshKnowledge();
      if (collectionDraft.id === collection.id) setCollectionDraft(blankCollection);
    });
  }

  async function uploadFile(file: File) {
    if (!uploadCollectionId) throw new Error("Select a collection before uploading.");
    await run("document-upload", async () => {
      await uploadKnowledgeDocument(uploadCollectionId, file);
      await refreshKnowledge();
      setNotice(`${file.name} was extracted and indexed.`);
    });
  }

  async function reindexDocument(document: KnowledgeDocument) {
    await run(`document-reindex-${document.id}`, async () => {
      await apiRequest<KnowledgeDocument>(`/api/knowledge-documents/${document.id}/reindex`, {
        method: "POST",
      });
      await refreshKnowledge();
    });
  }

  async function removeDocument(document: KnowledgeDocument) {
    if (!window.confirm(`Delete ${document.filename} from the private knowledge base?`)) return;
    await run(`document-delete-${document.id}`, async () => {
      await apiRequest<void>(`/api/knowledge-documents/${document.id}`, { method: "DELETE" });
      await refreshKnowledge();
    });
  }

  async function loadScope(conversationId: string) {
    setScopeConversationId(conversationId);
    if (!conversationId) {
      setScope(null);
      return;
    }
    await run("scope-load", async () => {
      setScope(
        await apiRequest<ConversationRetrievalSettings>(
          `/api/conversations/${conversationId}/retrieval-settings`,
        ),
      );
    });
  }

  async function saveScope() {
    if (!scope || !scopeConversationId) return;
    await run("scope-save", async () => {
      const next = await apiRequest<ConversationRetrievalSettings>(
        `/api/conversations/${scopeConversationId}/retrieval-settings`,
        {
          method: "PUT",
          body: JSON.stringify({
            memory_enabled: scope.memory_enabled,
            rag_enabled: scope.rag_enabled,
            collection_ids: scope.collections.map((collection) => collection.id),
          }),
        },
      );
      setScope(next);
      setNotice("Conversation retrieval scope saved.");
    });
  }

  function toggleScopeCollection(collection: KnowledgeCollection) {
    if (!scope) return;
    const selected = scope.collections.some((item) => item.id === collection.id);
    setScope({
      ...scope,
      collections: selected
        ? scope.collections.filter((item) => item.id !== collection.id)
        : [...scope.collections, collection],
    });
  }

  return (
    <div className={styles.stack}>
      {(error || notice) && (
        <div className={`${styles.banner} ${error ? styles.error : styles.notice}`}>
          {error ?? notice}
        </div>
      )}

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <p>Retrieval model</p>
            <h2>Optional semantic search</h2>
            <span>Without an embedding model, Aster keeps using lexical retrieval.</span>
          </div>
          <button
            className={styles.secondaryButton}
            disabled={busy !== null}
            onClick={reindexMemories}
            type="button"
          >
            <Icon name="refresh" /> Reindex memories
          </button>
        </div>
        <label className={styles.field}>
          <span>Embedding model</span>
          <select
            disabled={busy !== null}
            onChange={(event) => updateEmbeddingModel(event.target.value)}
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
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <p>Approved memory</p>
            <h2>Facts Aster may remember</h2>
            <span>Global memories apply everywhere. Persona memories stay inside that identity.</span>
          </div>
          <div className={styles.actions}>
            <button className={styles.secondaryButton} onClick={exportMemories} type="button">
              <Icon name="download" /> Export
            </button>
            <button
              className={styles.secondaryButton}
              onClick={() => importRef.current?.click()}
              type="button"
            >
              <Icon name="upload" /> Import
            </button>
            <input
              accept="application/json,.json"
              className={styles.hiddenInput}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void importMemories(file);
                event.target.value = "";
              }}
              ref={importRef}
              type="file"
            />
          </div>
        </div>

        <div className={styles.editorGrid}>
          <label className={`${styles.field} ${styles.wideField}`}>
            <span>Memory</span>
            <textarea
              maxLength={4000}
              onChange={(event) =>
                setMemoryDraft({ ...memoryDraft, content: event.target.value })
              }
              placeholder="The user prefers direct technical answers."
              rows={3}
              value={memoryDraft.content}
            />
          </label>
          <label className={styles.field}>
            <span>Category</span>
            <select
              onChange={(event) =>
                setMemoryDraft({
                  ...memoryDraft,
                  category: event.target.value as MemoryCategory,
                })
              }
              value={memoryDraft.category}
            >
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.field}>
            <span>Scope</span>
            <select
              onChange={(event) =>
                setMemoryDraft({ ...memoryDraft, persona_id: event.target.value || null })
              }
              value={memoryDraft.persona_id ?? ""}
            >
              <option value="">Global</option>
              {initialPersonas.map((persona) => (
                <option key={persona.id} value={persona.id}>
                  {persona.name}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.checkboxField}>
            <input
              checked={memoryDraft.enabled}
              onChange={(event) =>
                setMemoryDraft({ ...memoryDraft, enabled: event.target.checked })
              }
              type="checkbox"
            />
            Enabled
          </label>
          <div className={styles.actions}>
            {memoryDraft.id && (
              <button
                className={styles.secondaryButton}
                onClick={() => setMemoryDraft(blankMemory)}
                type="button"
              >
                Cancel
              </button>
            )}
            <button
              className={styles.primaryButton}
              disabled={busy !== null}
              onClick={saveMemoryDraft}
              type="button"
            >
              {memoryDraft.id ? "Update memory" : "Save memory"}
            </button>
          </div>
        </div>

        <div className={styles.list}>
          {memories.length === 0 ? (
            <div className={styles.empty}>No approved memories yet.</div>
          ) : (
            memories.map((memory) => (
              <article className={styles.row} key={memory.id}>
                <div className={styles.rowMain}>
                  <div className={styles.badges}>
                    <span>{memory.category}</span>
                    <span>{memory.persona_name ?? "Global"}</span>
                    <span>{memory.has_embedding ? "Embedded" : "Lexical"}</span>
                    {!memory.enabled && <span>Disabled</span>}
                  </div>
                  <p>{memory.content}</p>
                </div>
                <div className={styles.actions}>
                  <button
                    aria-label="Edit memory"
                    className={styles.iconButton}
                    onClick={() =>
                      setMemoryDraft({
                        id: memory.id,
                        content: memory.content,
                        category: memory.category,
                        persona_id: memory.persona_id,
                        enabled: memory.enabled,
                      })
                    }
                    type="button"
                  >
                    <Icon name="edit" />
                  </button>
                  <button
                    aria-label="Delete memory"
                    className={styles.iconButton}
                    onClick={() => removeMemory(memory)}
                    type="button"
                  >
                    <Icon name="trash" />
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <p>Suggestions</p>
            <h2>Review before remembering</h2>
            <span>The Utility model may suggest candidates. Nothing is saved automatically.</span>
          </div>
          <div className={styles.inlineControl}>
            <select
              onChange={(event) => setSuggestionConversationId(event.target.value)}
              value={suggestionConversationId}
            >
              <option value="">Select conversation</option>
              {initialConversations.map((conversation) => (
                <option key={conversation.id} value={conversation.id}>
                  {conversation.title}
                </option>
              ))}
            </select>
            <button
              className={styles.primaryButton}
              disabled={!suggestionConversationId || busy !== null}
              onClick={generateSuggestions}
              type="button"
            >
              Generate suggestions
            </button>
          </div>
        </div>
        <div className={styles.list}>
          {suggestions.length === 0 ? (
            <div className={styles.empty}>No pending suggestions.</div>
          ) : (
            suggestions.map((suggestion) => (
              <article className={styles.row} key={suggestion.id}>
                <div className={styles.rowMain}>
                  <div className={styles.badges}>
                    <span>{suggestion.category}</span>
                    <span>Pending approval</span>
                  </div>
                  <p>{suggestion.content}</p>
                </div>
                <div className={styles.actions}>
                  <button
                    className={styles.secondaryButton}
                    onClick={() => rejectSuggestion(suggestion)}
                    type="button"
                  >
                    Reject
                  </button>
                  <button
                    className={styles.primaryButton}
                    onClick={() => acceptSuggestion(suggestion)}
                    type="button"
                  >
                    Accept
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <p>Knowledge collections</p>
            <h2>Private document retrieval</h2>
            <span>Text is extracted and indexed. Original uploads are not exposed by a public route.</span>
          </div>
        </div>
        <div className={styles.editorGrid}>
          <label className={styles.field}>
            <span>Name</span>
            <input
              maxLength={120}
              onChange={(event) =>
                setCollectionDraft({ ...collectionDraft, name: event.target.value })
              }
              value={collectionDraft.name}
            />
          </label>
          <label className={`${styles.field} ${styles.wideField}`}>
            <span>Description</span>
            <input
              maxLength={500}
              onChange={(event) =>
                setCollectionDraft({ ...collectionDraft, description: event.target.value })
              }
              value={collectionDraft.description}
            />
          </label>
          <label className={styles.checkboxField}>
            <input
              checked={collectionDraft.enabled}
              onChange={(event) =>
                setCollectionDraft({ ...collectionDraft, enabled: event.target.checked })
              }
              type="checkbox"
            />
            Enabled
          </label>
          <label className={styles.checkboxField}>
            <input
              checked={collectionDraft.default_enabled}
              disabled={!collectionDraft.enabled}
              onChange={(event) =>
                setCollectionDraft({
                  ...collectionDraft,
                  default_enabled: event.target.checked,
                })
              }
              type="checkbox"
            />
            Add to new conversations
          </label>
          <div className={styles.actions}>
            {collectionDraft.id && (
              <button
                className={styles.secondaryButton}
                onClick={() => setCollectionDraft(blankCollection)}
                type="button"
              >
                Cancel
              </button>
            )}
            <button
              className={styles.primaryButton}
              disabled={busy !== null}
              onClick={saveCollectionDraft}
              type="button"
            >
              {collectionDraft.id ? "Update collection" : "Create collection"}
            </button>
          </div>
        </div>

        <div className={styles.collectionGrid}>
          {collections.map((collection) => (
            <article className={styles.collectionCard} key={collection.id}>
              <div>
                <div className={styles.badges}>
                  <span>{collection.enabled ? "Enabled" : "Disabled"}</span>
                  {collection.default_enabled && <span>New chat default</span>}
                </div>
                <h3>{collection.name}</h3>
                <p>{collection.description || "No description."}</p>
                <small>
                  {collection.ready_document_count}/{collection.document_count} ready ·{" "}
                  {collection.chunk_count} chunks
                </small>
              </div>
              <div className={styles.actions}>
                <button
                  className={styles.secondaryButton}
                  onClick={() =>
                    setCollectionDraft({
                      id: collection.id,
                      name: collection.name,
                      description: collection.description,
                      enabled: collection.enabled,
                      default_enabled: collection.default_enabled,
                    })
                  }
                  type="button"
                >
                  Edit
                </button>
                <button
                  className={styles.iconButton}
                  onClick={() => removeCollection(collection)}
                  type="button"
                >
                  <Icon name="trash" />
                </button>
              </div>
            </article>
          ))}
        </div>

        <div className={styles.uploadBar}>
          <select
            onChange={(event) => setUploadCollectionId(event.target.value)}
            value={uploadCollectionId}
          >
            <option value="">Select collection</option>
            {collections
              .filter((collection) => collection.enabled)
              .map((collection) => (
                <option key={collection.id} value={collection.id}>
                  {collection.name}
                </option>
              ))}
          </select>
          <button
            className={styles.primaryButton}
            disabled={!uploadCollectionId || busy !== null}
            onClick={() => uploadRef.current?.click()}
            type="button"
          >
            <Icon name="upload" /> Upload document
          </button>
          <input
            accept=".txt,.md,.markdown,.rst,.json,.jsonl,.csv,.tsv,.xml,.yaml,.yml,.toml,.ini,.log,.html,.htm,.pdf,text/*,application/pdf,application/json"
            className={styles.hiddenInput}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void uploadFile(file);
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
            documents.map((document) => (
              <article className={styles.row} key={document.id}>
                <div className={styles.rowMain}>
                  <div className={styles.badges}>
                    <span>{document.collection_name}</span>
                    <span>{document.status}</span>
                    <span>{document.embedded_chunk_count ? "Hybrid" : "Lexical"}</span>
                  </div>
                  <p>{document.filename}</p>
                  <small>
                    {formatBytes(document.size_bytes)} · {document.chunk_count} chunks
                    {document.error_message ? ` · ${document.error_message}` : ""}
                  </small>
                </div>
                <div className={styles.actions}>
                  <button
                    className={styles.secondaryButton}
                    onClick={() => reindexDocument(document)}
                    type="button"
                  >
                    Reindex
                  </button>
                  <button
                    className={styles.iconButton}
                    onClick={() => removeDocument(document)}
                    type="button"
                  >
                    <Icon name="trash" />
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <p>Conversation scope</p>
            <h2>Choose what one chat may retrieve</h2>
            <span>Changes apply to later responses and never rewrite existing messages.</span>
          </div>
        </div>
        <div className={styles.scopeGrid}>
          <label className={styles.field}>
            <span>Conversation</span>
            <select
              onChange={(event) => loadScope(event.target.value)}
              value={scopeConversationId}
            >
              <option value="">Select conversation</option>
              {initialConversations.map((conversation) => (
                <option key={conversation.id} value={conversation.id}>
                  {conversation.title}
                </option>
              ))}
            </select>
          </label>
          {scope && (
            <>
              <label className={styles.checkboxField}>
                <input
                  checked={scope.memory_enabled}
                  onChange={(event) =>
                    setScope({ ...scope, memory_enabled: event.target.checked })
                  }
                  type="checkbox"
                />
                Use approved memory
              </label>
              <label className={styles.checkboxField}>
                <input
                  checked={scope.rag_enabled}
                  onChange={(event) =>
                    setScope({ ...scope, rag_enabled: event.target.checked })
                  }
                  type="checkbox"
                />
                Use knowledge retrieval
              </label>
              <div className={styles.scopeCollections}>
                {collections
                  .filter((collection) => collection.enabled)
                  .map((collection) => (
                    <label className={styles.checkboxField} key={collection.id}>
                      <input
                        checked={scope.collections.some((item) => item.id === collection.id)}
                        onChange={() => toggleScopeCollection(collection)}
                        type="checkbox"
                      />
                      {collection.name}
                    </label>
                  ))}
              </div>
              <button
                className={styles.primaryButton}
                disabled={busy !== null}
                onClick={saveScope}
                type="button"
              >
                Save conversation scope
              </button>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
