"use client";

import { useState, type FormEvent } from "react";

import {
  apiRequest,
  type CanonicalMessage,
  type CompositionPreview,
  type PersonaSettings,
} from "../../../lib/api";

type PersonaDraft = Pick<
  PersonaSettings,
  "name" | "instructions" | "enabled" | "instruction_role"
>;

export function PersonaSettingsForm({
  initialPersona,
  initialError,
}: {
  initialPersona: PersonaSettings;
  initialError: string | null;
}) {
  const [persona, setPersona] = useState<PersonaDraft>({
    name: initialPersona.name,
    instructions: initialPersona.instructions,
    enabled: initialPersona.enabled,
    instruction_role: initialPersona.instruction_role,
  });
  const [previewMessage, setPreviewMessage] = useState(
    "Explain why system and user messages should remain separate.",
  );
  const [preview, setPreview] = useState<CanonicalMessage[]>([]);
  const [busy, setBusy] = useState<"save" | "preview" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);

  async function savePersona(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setBusy("save");
    setNotice(null);
    setError(null);

    try {
      const saved = await apiRequest<PersonaSettings>("/api/persona", {
        method: "PUT",
        body: JSON.stringify(persona),
      });
      setPersona({
        name: saved.name,
        instructions: saved.instructions,
        enabled: saved.enabled,
        instruction_role: saved.instruction_role,
      });
      setNotice("Persona saved. New model requests will use this configuration.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the persona.");
    } finally {
      setBusy(null);
    }
  }

  async function previewComposition() {
    if (!previewMessage.trim()) {
      setError("Enter a sample user message first.");
      return;
    }

    setBusy("preview");
    setNotice(null);
    setError(null);

    try {
      const result = await apiRequest<CompositionPreview>(
        "/api/message-composition/preview",
        {
          method: "POST",
          body: JSON.stringify({ user_message: previewMessage }),
        },
      );
      setPreview(result.messages);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not build the preview.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="persona-layout">
      <section className="panel persona-editor">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Identity</p>
            <h2>Global persona</h2>
            <p className="section-copy">
              This is instruction context, not chat history. Aster never stores or sends it as a
              user message.
            </p>
          </div>
          <span className={`pill ${persona.enabled ? "pill-success" : ""}`}>
            {persona.enabled ? "Enabled" : "Disabled"}
          </span>
        </div>

        {(notice || error) && (
          <div className={`banner ${error ? "banner-error" : "banner-success"}`} role="status">
            {error ?? notice}
          </div>
        )}

        <form className="form-grid persona-form" onSubmit={savePersona}>
          <label>
            <span>Name</span>
            <input
              maxLength={120}
              value={persona.name}
              onChange={(event) => setPersona({ ...persona, name: event.target.value })}
              placeholder="Personal Assistant"
            />
            <small className="form-help">
              When set, Aster composes it as: <code>Your name is …</code>
            </small>
          </label>

          <label>
            <span>Instruction role</span>
            <select
              value={persona.instruction_role}
              onChange={(event) =>
                setPersona({
                  ...persona,
                  instruction_role: event.target.value as PersonaDraft["instruction_role"],
                })
              }
            >
              <option value="developer">Developer</option>
              <option value="system">System</option>
            </select>
            <small className="form-help">
              Use system only for APIs that do not support the developer role.
            </small>
          </label>

          <label className="form-span-two">
            <span>Instructions</span>
            <textarea
              maxLength={100_000}
              rows={14}
              value={persona.instructions}
              onChange={(event) => setPersona({ ...persona, instructions: event.target.value })}
              placeholder="Describe the identity, tone, behavior, and boundaries you want every model to follow."
            />
          </label>

          <label className="checkbox-row form-span-two">
            <input
              type="checkbox"
              checked={persona.enabled}
              onChange={(event) => setPersona({ ...persona, enabled: event.target.checked })}
            />
            <span>Apply this persona to model requests</span>
          </label>

          <div className="form-actions form-span-two">
            <button className="button" disabled={busy !== null} type="submit">
              Save persona
            </button>
          </div>
        </form>
      </section>

      <section className="panel preview-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Preview</p>
            <h2>Canonical messages</h2>
            <p className="section-copy">
              The preview uses the last saved persona and shows the exact role and source separation
              the chat milestone will consume.
            </p>
          </div>
        </div>

        <label className="preview-input">
          <span>Sample user message</span>
          <textarea
            rows={5}
            value={previewMessage}
            onChange={(event) => setPreviewMessage(event.target.value)}
          />
        </label>

        <button
          className="button button-secondary"
          disabled={busy !== null}
          onClick={() => void previewComposition()}
        >
          Preview composition
        </button>

        {preview.length === 0 ? (
          <div className="empty-state preview-empty">
            Save the persona, then generate a preview to inspect the message roles.
          </div>
        ) : (
          <div className="message-preview-list">
            {preview.map((message, index) => (
              <article className="message-preview" key={`${message.role}-${index}`}>
                <div className="message-meta">
                  <span className="pill">{message.role}</span>
                  <span className="muted">source: {message.source}</span>
                </div>
                <pre>{message.content}</pre>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
