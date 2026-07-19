"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  apiRequest,
  type Persona,
  type PersonaPreferences,
} from "../../../lib/api";
import {
  notifySettingsUpdated,
  SummaryCard,
  SummaryGrid,
  UnsavedBadge,
  useUnsavedChanges,
} from "../settings-primitives";
import styles from "../simple-settings.module.css";

type PersonaDraft = Pick<
  Persona,
  "name" | "description" | "instructions" | "enabled" | "instruction_role"
>;

const blankDraft: PersonaDraft = {
  name: "",
  description: "",
  instructions: "",
  enabled: true,
  instruction_role: "developer",
};

function toDraft(persona: Persona): PersonaDraft {
  return {
    name: persona.name,
    description: persona.description,
    instructions: persona.instructions,
    enabled: persona.enabled,
    instruction_role: persona.instruction_role,
  };
}

function sameDraft(left: PersonaDraft, right: PersonaDraft): boolean {
  return (
    left.name === right.name &&
    left.description === right.description &&
    left.instructions === right.instructions &&
    left.enabled === right.enabled &&
    left.instruction_role === right.instruction_role
  );
}

export function SimplePersonaSettings({
  initialPersonas,
  initialPreferences,
  initialError,
}: {
  initialPersonas: Persona[];
  initialPreferences: PersonaPreferences;
  initialError: string | null;
}) {
  const router = useRouter();
  const [personas, setPersonas] = useState(initialPersonas);
  const [defaultPersonaId, setDefaultPersonaId] = useState(
    initialPreferences.default_persona?.id ?? null,
  );
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(
    initialPersonas[0]?.id ?? null,
  );
  const [draft, setDraft] = useState<PersonaDraft>(
    initialPersonas[0] ? toDraft(initialPersonas[0]) : blankDraft,
  );
  const [savedDraft, setSavedDraft] = useState<PersonaDraft>(
    initialPersonas[0] ? toDraft(initialPersonas[0]) : blankDraft,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);

  const selectedPersona = useMemo(
    () => personas.find((persona) => persona.id === selectedPersonaId) ?? null,
    [personas, selectedPersonaId],
  );
  const dirty = !sameDraft(draft, savedDraft);
  useUnsavedChanges(dirty);

  function clearStatus() {
    setNotice(null);
    setError(null);
  }

  function selectPersona(persona: Persona) {
    const next = toDraft(persona);
    setSelectedPersonaId(persona.id);
    setDraft(next);
    setSavedDraft(next);
    clearStatus();
  }

  function startNewPersona() {
    setSelectedPersonaId(null);
    setDraft(blankDraft);
    setSavedDraft(blankDraft);
    clearStatus();
  }

  async function refresh(preferredId?: string | null) {
    const [nextPersonas, nextPreferences] = await Promise.all([
      apiRequest<Persona[]>("/api/personas"),
      apiRequest<PersonaPreferences>("/api/persona-preferences"),
    ]);
    setPersonas(nextPersonas);
    setDefaultPersonaId(nextPreferences.default_persona?.id ?? null);
    const nextSelected =
      nextPersonas.find((persona) => persona.id === preferredId) ?? nextPersonas[0] ?? null;
    setSelectedPersonaId(nextSelected?.id ?? null);
    const nextDraft = nextSelected ? toDraft(nextSelected) : blankDraft;
    setDraft(nextDraft);
    setSavedDraft(nextDraft);
  }

  function completeUpdate(message: string) {
    setNotice(message);
    notifySettingsUpdated();
    router.refresh();
  }

  async function savePersona(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.name.trim()) {
      setError("Enter a persona name.");
      return;
    }
    if (busy) return;
    setBusy("save");
    clearStatus();
    try {
      const saved = await apiRequest<Persona>(
        selectedPersonaId ? `/api/personas/${selectedPersonaId}` : "/api/personas",
        {
          method: selectedPersonaId ? "PUT" : "POST",
          body: JSON.stringify({
            ...draft,
            name: draft.name.trim(),
            description: draft.description.trim(),
          }),
        },
      );
      await refresh(saved.id);
      completeUpdate(selectedPersonaId ? "Persona saved." : "Persona created.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the persona.");
    } finally {
      setBusy(null);
    }
  }

  async function makeDefault() {
    if (!selectedPersona || !selectedPersona.enabled || busy) return;
    setBusy("default");
    clearStatus();
    try {
      const result = await apiRequest<PersonaPreferences>("/api/persona-preferences", {
        method: "PUT",
        body: JSON.stringify({ default_persona_id: selectedPersona.id }),
      });
      setDefaultPersonaId(result.default_persona?.id ?? null);
      setPersonas((current) =>
        current.map((persona) => ({
          ...persona,
          is_default: persona.id === result.default_persona?.id,
        })),
      );
      completeUpdate("Default persona updated for new conversations.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not update the default persona.");
    } finally {
      setBusy(null);
    }
  }

  async function clearDefault() {
    if (busy || defaultPersonaId === null) return;
    setBusy("clear-default");
    clearStatus();
    try {
      await apiRequest<PersonaPreferences>("/api/persona-preferences", {
        method: "PUT",
        body: JSON.stringify({ default_persona_id: null }),
      });
      setDefaultPersonaId(null);
      setPersonas((current) => current.map((persona) => ({ ...persona, is_default: false })));
      completeUpdate("New conversations will start without a persona.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not clear the default persona.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div aria-busy={busy !== null} className={styles.root}>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}
      {!error && notice ? <div className={styles.notice} role="status">{notice}</div> : null}

      <SummaryGrid>
        <SummaryCard label="Personas" value={String(personas.length)} note="Reusable identities" />
        <SummaryCard
          label="Available"
          value={String(personas.filter((persona) => persona.enabled).length)}
          note="Enabled for new snapshots"
        />
        <SummaryCard
          label="Default"
          value={personas.find((persona) => persona.id === defaultPersonaId)?.name ?? "None"}
          note="Applied to new chats"
        />
      </SummaryGrid>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Persona library</h2>
            <p>Select an identity to edit or create a clean one without touching existing chat snapshots.</p>
          </div>
          <button
            className={styles.secondaryButton}
            disabled={busy !== null}
            onClick={startNewPersona}
            type="button"
          >
            New persona
          </button>
        </div>
        <div className={styles.sectionBody}>
          <div className={styles.cardGrid}>
            {personas.length === 0 ? (
              <div className={styles.empty}>Create a persona to define a reusable identity.</div>
            ) : (
              personas.map((persona) => (
                <button
                  aria-pressed={persona.id === selectedPersonaId}
                  className={styles.card}
                  disabled={busy !== null}
                  key={persona.id}
                  onClick={() => selectPersona(persona)}
                  style={
                    persona.id === selectedPersonaId
                      ? { borderColor: "var(--accent-border)", background: "var(--surface-selected)" }
                      : undefined
                  }
                  type="button"
                >
                  <div className={styles.badges}>
                    <span
                      className={`${styles.badge} ${persona.enabled ? styles.successBadge : styles.warningBadge}`}
                    >
                      {persona.enabled ? "Available" : "Disabled"}
                    </span>
                    {persona.id === defaultPersonaId ? (
                      <span className={`${styles.badge} ${styles.successBadge}`}>Default</span>
                    ) : null}
                  </div>
                  <div className={styles.cardMain}>
                    <strong>{persona.name}</strong>
                    <p>{persona.description || "No description."}</p>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>{selectedPersona ? selectedPersona.name : "New persona"}</h2>
            <p>Name the identity, describe when to use it, and write its instruction layer.</p>
          </div>
          <UnsavedBadge visible={dirty} />
        </div>
        <form className={styles.sectionBody} onSubmit={savePersona}>
          <div className={styles.formGrid}>
            <label className={styles.field}>
              <span>Name</span>
              <input
                disabled={busy !== null}
                maxLength={120}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                placeholder="Research assistant"
                required
                value={draft.name}
              />
            </label>
            <label className={styles.checkboxField}>
              <input
                checked={draft.enabled}
                disabled={busy !== null}
                onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
                type="checkbox"
              />
              Available for new conversation snapshots
            </label>
            <label className={styles.wideField}>
              <span>Description</span>
              <textarea
                disabled={busy !== null}
                maxLength={500}
                onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                placeholder="A short note describing when this persona should be used."
                rows={3}
                value={draft.description}
              />
            </label>
            <label className={`${styles.wideField} ${styles.instructions}`}>
              <span>Instructions</span>
              <textarea
                disabled={busy !== null}
                maxLength={100_000}
                onChange={(event) => setDraft({ ...draft, instructions: event.target.value })}
                placeholder="Describe identity, tone, behavior, knowledge boundaries, and response preferences."
                value={draft.instructions}
              />
            </label>
          </div>
          <div className={styles.actions}>
            {selectedPersonaId || dirty ? (
              <button
                className={styles.secondaryButton}
                disabled={busy !== null}
                onClick={() => {
                  if (selectedPersona) selectPersona(selectedPersona);
                  else startNewPersona();
                }}
                type="button"
              >
                Reset changes
              </button>
            ) : null}
            <button
              className={styles.primaryButton}
              disabled={busy !== null || !draft.name.trim() || (!dirty && Boolean(selectedPersonaId))}
              type="submit"
            >
              {busy === "save"
                ? "Saving persona"
                : selectedPersonaId
                  ? "Save persona"
                  : "Create persona"}
            </button>
          </div>
        </form>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Default for new chats</h2>
            <p>Existing conversations keep their frozen persona snapshot.</p>
          </div>
        </div>
        <div className={styles.sectionBody}>
          <div className={styles.statusRow}>
            <span className={styles.badge}>Current default</span>
            <strong>
              {personas.find((persona) => persona.id === defaultPersonaId)?.name ?? "No persona"}
            </strong>
          </div>
          <div className={styles.actions}>
            <button
              className={styles.secondaryButton}
              disabled={
                !selectedPersona ||
                !selectedPersona.enabled ||
                selectedPersona.id === defaultPersonaId ||
                busy !== null
              }
              onClick={() => void makeDefault()}
              type="button"
            >
              {busy === "default" ? "Updating default" : "Use selected persona"}
            </button>
            <button
              className={styles.secondaryButton}
              disabled={defaultPersonaId === null || busy !== null}
              onClick={() => void clearDefault()}
              type="button"
            >
              {busy === "clear-default" ? "Clearing default" : "Use no default"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
