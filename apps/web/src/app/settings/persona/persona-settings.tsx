"use client";

import { useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";

import {
  apiRequest,
  type CanonicalMessage,
  type CompositionPreview,
  type Conversation,
  type ConversationSummary,
  type Persona,
  type PersonaPreferences,
  type PersonaTransfer,
} from "../../../lib/api";
import styles from "./persona-library.module.css";

type PersonaDraft = Pick<
  Persona,
  "name" | "description" | "instructions" | "enabled" | "instruction_role"
>;

type BusyAction =
  | "save"
  | "default"
  | "duplicate"
  | "delete"
  | "preview"
  | "import"
  | "assign"
  | null;

const emptyDraft: PersonaDraft = {
  name: "",
  description: "",
  instructions: "",
  enabled: true,
  instruction_role: "developer",
};

function personaDraft(persona: Persona): PersonaDraft {
  return {
    name: persona.name,
    description: persona.description,
    instructions: persona.instructions,
    enabled: persona.enabled,
    instruction_role: persona.instruction_role,
  };
}

export function PersonaSettingsForm({
  initialPersonas,
  initialPreferences,
  initialConversations,
  initialError,
}: {
  initialPersonas: Persona[];
  initialPreferences: PersonaPreferences;
  initialConversations: ConversationSummary[];
  initialError: string | null;
}) {
  const [personas, setPersonas] = useState(initialPersonas);
  const [defaultPersonaId, setDefaultPersonaId] = useState(
    initialPreferences.default_persona?.id ?? null,
  );
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(
    initialPersonas[0]?.id ?? null,
  );
  const [draft, setDraft] = useState<PersonaDraft>(
    initialPersonas[0] ? personaDraft(initialPersonas[0]) : emptyDraft,
  );
  const [conversations, setConversations] = useState(initialConversations);
  const [selectedConversationId, setSelectedConversationId] = useState(
    initialConversations[0]?.id ?? "",
  );
  const [assignmentPersonaId, setAssignmentPersonaId] = useState("__unchanged");
  const [previewMessage, setPreviewMessage] = useState(
    "Explain the difference between a persona instruction and a user message.",
  );
  const [preview, setPreview] = useState<CanonicalMessage[]>([]);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);
  const importRef = useRef<HTMLInputElement>(null);

  const selectedPersona = useMemo(
    () => personas.find((persona) => persona.id === selectedPersonaId) ?? null,
    [personas, selectedPersonaId],
  );
  const selectedConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === selectedConversationId) ?? null,
    [conversations, selectedConversationId],
  );

  function clearStatus() {
    setNotice(null);
    setError(null);
  }

  function selectPersona(persona: Persona) {
    setSelectedPersonaId(persona.id);
    setDraft(personaDraft(persona));
    setPreview([]);
    clearStatus();
  }

  function startNewPersona() {
    setSelectedPersonaId(null);
    setDraft(emptyDraft);
    setPreview([]);
    clearStatus();
  }

  async function savePersona(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.name.trim()) {
      setError("Enter a persona name.");
      return;
    }
    setBusy("save");
    clearStatus();
    try {
      const saved = await apiRequest<Persona>(
        selectedPersonaId ? `/api/personas/${selectedPersonaId}` : "/api/personas",
        {
          method: selectedPersonaId ? "PUT" : "POST",
          body: JSON.stringify(draft),
        },
      );
      setPersonas((current) => {
        const exists = current.some((persona) => persona.id === saved.id);
        const next = exists
          ? current.map((persona) => (persona.id === saved.id ? saved : persona))
          : [saved, ...current];
        return next.map((persona) => ({
          ...persona,
          is_default: persona.id === (saved.is_default ? saved.id : defaultPersonaId),
        }));
      });
      if (saved.is_default) setDefaultPersonaId(saved.id);
      setSelectedPersonaId(saved.id);
      setDraft(personaDraft(saved));
      setNotice(
        selectedPersonaId
          ? "Persona saved. Existing conversation snapshots were not changed."
          : "Persona created.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the persona.");
    } finally {
      setBusy(null);
    }
  }

  async function makeDefault() {
    if (!selectedPersona || !selectedPersona.enabled) return;
    setBusy("default");
    clearStatus();
    try {
      const result = await apiRequest<PersonaPreferences>("/api/persona-preferences", {
        method: "PUT",
        body: JSON.stringify({ default_persona_id: selectedPersona.id }),
      });
      const nextDefaultId = result.default_persona?.id ?? null;
      setDefaultPersonaId(nextDefaultId);
      setPersonas((current) =>
        current.map((persona) => ({ ...persona, is_default: persona.id === nextDefaultId })),
      );
      setNotice("Default persona updated. New conversations will snapshot this persona.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not update the default persona.");
    } finally {
      setBusy(null);
    }
  }

  async function clearDefault() {
    setBusy("default");
    clearStatus();
    try {
      await apiRequest<PersonaPreferences>("/api/persona-preferences", {
        method: "PUT",
        body: JSON.stringify({ default_persona_id: null }),
      });
      setDefaultPersonaId(null);
      setPersonas((current) => current.map((persona) => ({ ...persona, is_default: false })));
      setNotice("Default persona cleared. New conversations will start without a persona.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not clear the default persona.");
    } finally {
      setBusy(null);
    }
  }

  async function duplicatePersona() {
    if (!selectedPersona) return;
    setBusy("duplicate");
    clearStatus();
    try {
      const duplicate = await apiRequest<Persona>(
        `/api/personas/${selectedPersona.id}/duplicate`,
        { method: "POST" },
      );
      setPersonas((current) => [duplicate, ...current]);
      setSelectedPersonaId(duplicate.id);
      setDraft(personaDraft(duplicate));
      setPreview([]);
      setNotice("Persona duplicated.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not duplicate the persona.");
    } finally {
      setBusy(null);
    }
  }

  async function deletePersona() {
    if (!selectedPersona) return;
    if (
      !window.confirm(
        `Delete “${selectedPersona.name}”? Conversation snapshots that already use it will remain intact.`,
      )
    ) {
      return;
    }
    setBusy("delete");
    clearStatus();
    try {
      await apiRequest(`/api/personas/${selectedPersona.id}`, { method: "DELETE" });
      const remaining = personas.filter((persona) => persona.id !== selectedPersona.id);
      setPersonas(remaining);
      if (defaultPersonaId === selectedPersona.id) setDefaultPersonaId(null);
      const next = remaining[0] ?? null;
      setSelectedPersonaId(next?.id ?? null);
      setDraft(next ? personaDraft(next) : emptyDraft);
      setPreview([]);
      setNotice("Persona deleted. Existing conversation snapshots were preserved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the persona.");
    } finally {
      setBusy(null);
    }
  }

  async function previewComposition() {
    if (!selectedPersonaId) {
      setError("Save the persona before previewing it.");
      return;
    }
    if (!previewMessage.trim()) {
      setError("Enter a sample user message first.");
      return;
    }
    setBusy("preview");
    clearStatus();
    try {
      const result = await apiRequest<CompositionPreview>(
        "/api/message-composition/preview",
        {
          method: "POST",
          body: JSON.stringify({
            user_message: previewMessage,
            persona_id: selectedPersonaId,
            use_default_persona: false,
          }),
        },
      );
      setPreview(result.messages);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not build the preview.");
    } finally {
      setBusy(null);
    }
  }

  function exportPersona() {
    if (!selectedPersona) return;
    const transfer: PersonaTransfer = {
      format: "aster-persona",
      version: 1,
      name: selectedPersona.name,
      description: selectedPersona.description,
      instructions: selectedPersona.instructions,
      enabled: selectedPersona.enabled,
      instruction_role: selectedPersona.instruction_role,
    };
    const blob = new Blob([`${JSON.stringify(transfer, null, 2)}\n`], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${safeFileName(selectedPersona.name)}.aster-persona.json`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function importPersona(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    if (file.size > 1_000_000) {
      setError("Persona exports must be smaller than 1 MB.");
      return;
    }
    setBusy("import");
    clearStatus();
    try {
      const transfer = parsePersonaTransfer(await file.text());
      const imported = await apiRequest<Persona>("/api/personas/import", {
        method: "POST",
        body: JSON.stringify(transfer),
      });
      setPersonas((current) => [imported, ...current]);
      setSelectedPersonaId(imported.id);
      setDraft(personaDraft(imported));
      if (imported.is_default) setDefaultPersonaId(imported.id);
      setNotice("Persona imported.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not import the persona.");
    } finally {
      setBusy(null);
    }
  }

  async function assignConversationPersona() {
    if (!selectedConversation || assignmentPersonaId === "__unchanged") return;
    if (
      selectedConversation.message_count > 0 &&
      !window.confirm(
        "Changing this conversation persona affects future responses only. Existing messages remain unchanged. Continue?",
      )
    ) {
      return;
    }
    setBusy("assign");
    clearStatus();
    try {
      const personaId = assignmentPersonaId === "__none" ? null : assignmentPersonaId;
      const updated = await apiRequest<Conversation>(
        `/api/conversations/${selectedConversation.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({ persona_id: personaId }),
        },
      );
      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === updated.id
            ? {
                ...conversation,
                persona_name: updated.persona?.name ?? null,
                updated_at: updated.updated_at,
              }
            : conversation,
        ),
      );
      setAssignmentPersonaId("__unchanged");
      setNotice(
        updated.persona
          ? `Conversation now uses a frozen snapshot of ${updated.persona.name}.`
          : "Conversation will continue without a persona.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not update the conversation persona.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={styles.layout}>
      <aside className={styles.library}>
        <div className={styles.libraryHeader}>
          <div>
            <p className="eyebrow">Library</p>
            <h2>Personas</h2>
          </div>
          <button className={styles.compactButton} onClick={startNewPersona} type="button">
            New
          </button>
        </div>
        <div className={styles.personaList}>
          {personas.length === 0 ? (
            <div className={styles.emptyLibrary}>
              Create a persona to define a reusable identity and instruction layer.
            </div>
          ) : (
            personas.map((persona) => (
              <button
                className={`${styles.personaItem} ${
                  selectedPersonaId === persona.id ? styles.personaItemSelected : ""
                }`}
                key={persona.id}
                onClick={() => selectPersona(persona)}
                type="button"
              >
                <span className={styles.avatar}>{persona.name.slice(0, 2)}</span>
                <span className={styles.personaCopy}>
                  <strong>{persona.name || "Unnamed persona"}</strong>
                  <small>
                    {persona.enabled ? persona.description || persona.instruction_role : "Disabled"}
                  </small>
                </span>
                {persona.id === defaultPersonaId && <span className={styles.badge}>Default</span>}
              </button>
            ))
          )}
        </div>
      </aside>

      <section className={styles.editor}>
        <div className={styles.editorHeader}>
          <div>
            <p className="eyebrow">Identity</p>
            <h2>{selectedPersona ? selectedPersona.name : "New persona"}</h2>
            <p>
              Library changes never rewrite persona snapshots already stored in conversations.
            </p>
          </div>
          <div className={styles.actions}>
            <button
              className={styles.secondaryButton}
              disabled={!selectedPersona || busy !== null}
              onClick={exportPersona}
              type="button"
            >
              Export
            </button>
            <button
              className={styles.secondaryButton}
              disabled={busy !== null}
              onClick={() => importRef.current?.click()}
              type="button"
            >
              Import
            </button>
            <input
              accept=".json,application/json"
              className={styles.hiddenInput}
              onChange={(event) => void importPersona(event)}
              ref={importRef}
              type="file"
            />
          </div>
        </div>

        <div className={styles.editorBody}>
          {(notice || error) && (
            <div className={error ? styles.error : styles.notice} role="status">
              {error ?? notice}
            </div>
          )}

          <form onSubmit={(event) => void savePersona(event)}>
            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span>Name</span>
                <input
                  maxLength={120}
                  onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                  placeholder="Research assistant"
                  value={draft.name}
                />
              </label>
              <label className={styles.field}>
                <span>Instruction role</span>
                <select
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      instruction_role: event.target.value as PersonaDraft["instruction_role"],
                    })
                  }
                  value={draft.instruction_role}
                >
                  <option value="developer">Developer</option>
                  <option value="system">System</option>
                </select>
              </label>
              <label className={styles.fieldWide}>
                <span>Description</span>
                <textarea
                  maxLength={500}
                  onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                  placeholder="A short note to identify when this persona should be used."
                  rows={3}
                  value={draft.description}
                />
              </label>
              <label className={styles.fieldWide}>
                <span>Instructions</span>
                <textarea
                  maxLength={100_000}
                  onChange={(event) => setDraft({ ...draft, instructions: event.target.value })}
                  placeholder="Describe the identity, tone, behavior, and boundaries."
                  value={draft.instructions}
                />
              </label>
              <label className={styles.checkbox}>
                <input
                  checked={draft.enabled}
                  onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
                  type="checkbox"
                />
                <span>Available for new conversation snapshots</span>
              </label>
            </div>

            <div className={styles.actions} style={{ marginTop: 16 }}>
              <button
                className={styles.primaryButton}
                disabled={busy !== null || !draft.name.trim()}
                type="submit"
              >
                {selectedPersona ? "Save persona" : "Create persona"}
              </button>
              <button
                className={styles.secondaryButton}
                disabled={!selectedPersona || !selectedPersona.enabled || busy !== null}
                onClick={() => void makeDefault()}
                type="button"
              >
                Make default
              </button>
              <button
                className={styles.secondaryButton}
                disabled={defaultPersonaId === null || busy !== null}
                onClick={() => void clearDefault()}
                type="button"
              >
                Clear default
              </button>
              <button
                className={styles.secondaryButton}
                disabled={!selectedPersona || busy !== null}
                onClick={() => void duplicatePersona()}
                type="button"
              >
                Duplicate
              </button>
              <button
                className={styles.dangerButton}
                disabled={!selectedPersona || busy !== null}
                onClick={() => void deletePersona()}
                type="button"
              >
                Delete
              </button>
            </div>
          </form>

          <div className={styles.preview}>
            <div>
              <p className="eyebrow">Preview</p>
              <p className="muted">
                Inspect the canonical message roles generated by the last saved version.
              </p>
            </div>
            <div className={styles.previewControls}>
              <textarea
                onChange={(event) => setPreviewMessage(event.target.value)}
                value={previewMessage}
              />
              <button
                className={styles.secondaryButton}
                disabled={!selectedPersona || busy !== null}
                onClick={() => void previewComposition()}
                type="button"
              >
                Preview
              </button>
            </div>
            {preview.length > 0 && (
              <div className={styles.previewMessages}>
                {preview.map((message, index) => (
                  <article className={styles.previewMessage} key={`${message.role}-${index}`}>
                    <header>
                      <span>{message.role}</span>
                      <span>source: {message.source}</span>
                    </header>
                    <pre>{message.content}</pre>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className={styles.assignment}>
        <div className={styles.assignmentHeader}>
          <div>
            <p className="eyebrow">Conversation scope</p>
            <h2>Assign a persona snapshot</h2>
            <p>
              New chats inherit the default. Existing chats keep their frozen snapshot until you
              explicitly replace it here.
            </p>
          </div>
        </div>
        <div className={styles.assignmentBody}>
          <label className={styles.assignmentField}>
            <span>Conversation</span>
            <select
              onChange={(event) => {
                setSelectedConversationId(event.target.value);
                setAssignmentPersonaId("__unchanged");
              }}
              value={selectedConversationId}
            >
              {conversations.length === 0 && <option value="">No conversations</option>}
              {conversations.map((conversation) => (
                <option key={conversation.id} value={conversation.id}>
                  {conversation.title} · {conversation.persona_name ?? "No persona"}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.assignmentField}>
            <span>Future responses use</span>
            <select
              disabled={!selectedConversation}
              onChange={(event) => setAssignmentPersonaId(event.target.value)}
              value={assignmentPersonaId}
            >
              <option value="__unchanged">Keep current snapshot</option>
              <option value="__none">No persona</option>
              {personas
                .filter((persona) => persona.enabled)
                .map((persona) => (
                  <option key={persona.id} value={persona.id}>
                    {persona.name}
                  </option>
                ))}
            </select>
          </label>
          <button
            className={styles.primaryButton}
            disabled={
              !selectedConversation || assignmentPersonaId === "__unchanged" || busy !== null
            }
            onClick={() => void assignConversationPersona()}
            type="button"
          >
            Apply snapshot
          </button>
        </div>
      </section>
    </div>
  );
}

function parsePersonaTransfer(raw: string): PersonaTransfer {
  const value = JSON.parse(raw) as unknown;
  if (!isRecord(value)) throw new Error("The selected file does not contain a JSON object.");
  if (value.format !== "aster-persona" || value.version !== 1) {
    throw new Error("This is not a supported Aster persona export.");
  }
  if (typeof value.name !== "string" || !value.name.trim()) {
    throw new Error("The persona export does not contain a valid name.");
  }
  if (
    typeof value.description !== "string" ||
    typeof value.instructions !== "string" ||
    typeof value.enabled !== "boolean" ||
    (value.instruction_role !== "developer" && value.instruction_role !== "system")
  ) {
    throw new Error("The persona export contains invalid fields.");
  }
  return value as PersonaTransfer;
}

function safeFileName(value: string): string {
  const normalized = value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return normalized || "aster-persona";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
