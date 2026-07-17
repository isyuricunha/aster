"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { ConversationSummary, ModelPreferences } from "../../lib/api";
import {
  formatBytes,
  type ImageGallery,
  type ImageModelProfile,
  type ImageOperation,
  updateImageProfile,
} from "../../lib/image-api";
import { Icon } from "../ui/icons";
import styles from "./images.module.css";

type ProfileDraft = {
  supports_generation: boolean;
  supports_editing: boolean;
  supports_multiple_inputs: boolean;
  supports_masks: boolean;
  max_input_images: number;
  default_size: string;
  default_quality: string;
  default_output_format: "png" | "jpeg" | "webp";
  default_background: string;
  default_count: number;
  default_input_fidelity: string;
  provider_parameters: string;
};

function profileDraft(profile: ImageModelProfile): ProfileDraft {
  return {
    supports_generation: profile.supports_generation,
    supports_editing: profile.supports_editing,
    supports_multiple_inputs: profile.supports_multiple_inputs,
    supports_masks: profile.supports_masks,
    max_input_images: profile.max_input_images,
    default_size: profile.default_size ?? "",
    default_quality: profile.default_quality ?? "",
    default_output_format: profile.default_output_format,
    default_background: profile.default_background ?? "",
    default_count: profile.default_count,
    default_input_fidelity: profile.default_input_fidelity ?? "",
    provider_parameters: JSON.stringify(profile.provider_parameters, null, 2),
  };
}

export function ImageWorkspace({
  initialGallery,
  initialProfiles,
  initialPreferences,
  conversations,
  initialError,
}: {
  initialGallery: ImageGallery;
  initialProfiles: ImageModelProfile[];
  initialPreferences: ModelPreferences | null;
  conversations: ConversationSummary[];
  initialError: string | null;
}) {
  const [profiles, setProfiles] = useState(initialProfiles);
  const [selected, setSelected] = useState<ImageOperation | null>(initialGallery.items[0] ?? null);
  const [typeFilter, setTypeFilter] = useState<"all" | "generation" | "edit">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "completed" | "failed">("all");
  const [conversationFilter, setConversationFilter] = useState("all");
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ProfileDraft | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(initialError);

  const conversationNames = useMemo(
    () => new Map(conversations.map((conversation) => [conversation.id, conversation.title])),
    [conversations],
  );
  const visible = initialGallery.items.filter((operation) => {
    if (typeFilter !== "all" && operation.operation_type !== typeFilter) return false;
    if (statusFilter !== "all" && operation.status !== statusFilter) return false;
    if (conversationFilter !== "all" && operation.conversation_id !== conversationFilter) return false;
    return true;
  });
  const selectedImageModel = initialPreferences?.image;
  const resolvedModel = selectedImageModel ?? initialPreferences?.primary ?? null;
  const resolvedProfile = profiles.find((profile) => profile.model_id === resolvedModel?.id);
  const imageReady = Boolean(
    resolvedModel &&
      resolvedProfile?.endpoint_enabled &&
      resolvedProfile.is_available &&
      (resolvedProfile.supports_generation || resolvedProfile.supports_editing),
  );

  function beginProfile(profile: ImageModelProfile) {
    setEditingProfileId(profile.model_id);
    setDraft(profileDraft(profile));
    setError(null);
  }

  async function saveProfile(profile: ImageModelProfile) {
    if (!draft || saving) return;
    setSaving(true);
    setError(null);
    try {
      const providerParameters = JSON.parse(draft.provider_parameters || "{}") as unknown;
      if (!providerParameters || Array.isArray(providerParameters) || typeof providerParameters !== "object") {
        throw new Error("Provider parameters must be a JSON object.");
      }
      const updated = await updateImageProfile(profile.model_id, {
        supports_generation: draft.supports_generation,
        supports_editing: draft.supports_editing,
        supports_multiple_inputs: draft.supports_multiple_inputs,
        supports_masks: draft.supports_masks,
        max_input_images: draft.supports_multiple_inputs ? draft.max_input_images : 1,
        default_size: draft.default_size.trim() || null,
        default_quality: draft.default_quality.trim() || null,
        default_output_format: draft.default_output_format,
        default_background: draft.default_background.trim() || null,
        default_count: draft.default_count,
        default_input_fidelity: draft.default_input_fidelity.trim() || null,
        provider_parameters: providerParameters as Record<string, unknown>,
      });
      setProfiles((current) =>
        current.map((item) => (item.model_id === updated.model_id ? updated : item)),
      );
      setEditingProfileId(null);
      setDraft(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the image profile.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.workspace}>
      {error ? <div className={styles.error}>{error}</div> : null}

      <section className={styles.statusCard}>
        <div>
          <span className={imageReady ? styles.readyDot : styles.missingDot} />
          <div>
            <strong>{imageReady ? "Image operations ready" : "Image model configuration required"}</strong>
            <p>
              {resolvedModel
                ? `${resolvedModel.endpoint_name} / ${resolvedModel.model_id}`
                : "Select an Image model, or use a compatible Primary model."}
            </p>
          </div>
        </div>
        <Link href="/settings/models">Choose model roles</Link>
      </section>

      <section className={styles.section}>
        <header className={styles.sectionHeader}>
          <div>
            <p>History</p>
            <h2>Private gallery</h2>
            <span>{initialGallery.total} persisted image operations</span>
          </div>
          <div className={styles.filters}>
            <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as typeof typeFilter)}>
              <option value="all">All operations</option>
              <option value="generation">Generated</option>
              <option value="edit">Edited</option>
            </select>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}
            >
              <option value="all">All states</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
            <select value={conversationFilter} onChange={(event) => setConversationFilter(event.target.value)}>
              <option value="all">All conversations</option>
              {conversations.map((conversation) => (
                <option key={conversation.id} value={conversation.id}>
                  {conversation.title}
                </option>
              ))}
            </select>
          </div>
        </header>

        {visible.length === 0 ? (
          <div className={styles.empty}>
            <Icon name="images" size={28} />
            <strong>No images match these filters.</strong>
            <span>Generate or edit an image from the chat composer.</span>
          </div>
        ) : (
          <div className={styles.galleryLayout}>
            <div className={styles.grid}>
              {visible.map((operation) => {
                const cover = operation.outputs[0] ?? operation.inputs[0];
                return (
                  <button
                    className={`${styles.tile} ${selected?.id === operation.id ? styles.selected : ""}`}
                    key={operation.id}
                    onClick={() => setSelected(operation)}
                    type="button"
                  >
                    {cover ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img alt="" src={cover.content_url} />
                    ) : (
                      <div className={styles.failedPreview}>
                        <Icon name="images" size={28} />
                        <span>{operation.status}</span>
                      </div>
                    )}
                    <div>
                      <strong>{operation.operation_type === "edit" ? "Edited" : "Generated"}</strong>
                      <span>{operation.prompt}</span>
                    </div>
                  </button>
                );
              })}
            </div>

            {selected ? (
              <aside className={styles.details}>
                <div className={styles.detailHeading}>
                  <div>
                    <span>{selected.operation_type}</span>
                    <h3>{selected.status}</h3>
                  </div>
                  <Link href={`/?conversation=${selected.conversation_id}`}>
                    <Icon name="chat" size={14} />
                    Open chat
                  </Link>
                </div>
                {selected.outputs.length ? (
                  <div className={styles.outputStrip}>
                    {selected.outputs.map((output) => (
                      <a href={output.content_url} key={output.id} target="_blank">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img alt="Generated output" src={output.content_url} />
                      </a>
                    ))}
                  </div>
                ) : null}
                <dl>
                  <div>
                    <dt>Prompt</dt>
                    <dd>{selected.prompt}</dd>
                  </div>
                  {selected.revised_prompt ? (
                    <div>
                      <dt>Revised prompt</dt>
                      <dd>{selected.revised_prompt}</dd>
                    </div>
                  ) : null}
                  <div>
                    <dt>Model</dt>
                    <dd>{selected.provider_model_id}</dd>
                  </div>
                  <div>
                    <dt>Conversation</dt>
                    <dd>{conversationNames.get(selected.conversation_id) ?? selected.conversation_id}</dd>
                  </div>
                  <div>
                    <dt>Parameters</dt>
                    <dd><code>{JSON.stringify(selected.parameters)}</code></dd>
                  </div>
                  {selected.outputs[0] ? (
                    <div>
                      <dt>Output</dt>
                      <dd>
                        {selected.outputs[0].width}×{selected.outputs[0].height} · {formatBytes(selected.outputs[0].size_bytes)}
                      </dd>
                    </div>
                  ) : null}
                  {selected.error_message ? (
                    <div>
                      <dt>Error</dt>
                      <dd>{selected.error_message}</dd>
                    </div>
                  ) : null}
                </dl>
              </aside>
            ) : null}
          </div>
        )}
      </section>

      <section className={styles.section}>
        <header className={styles.sectionHeader}>
          <div>
            <p>Provider contracts</p>
            <h2>Image model capabilities</h2>
            <span>Capabilities are explicit. Aster never guesses them from a model name.</span>
          </div>
        </header>
        <div className={styles.profileList}>
          {profiles.map((profile) => {
            const editing = editingProfileId === profile.model_id && draft;
            return (
              <article className={styles.profileCard} key={profile.model_id}>
                <header>
                  <div>
                    <strong>{profile.provider_model_id}</strong>
                    <span>{profile.endpoint_name}</span>
                  </div>
                  <button onClick={() => beginProfile(profile)} type="button">
                    <Icon name="edit" size={13} />
                    Configure
                  </button>
                </header>
                {editing ? (
                  <div className={styles.profileForm}>
                    <div className={styles.capabilities}>
                      <label><input checked={draft.supports_generation} onChange={(event) => setDraft({ ...draft, supports_generation: event.target.checked })} type="checkbox" /> Generation</label>
                      <label><input checked={draft.supports_editing} onChange={(event) => setDraft({ ...draft, supports_editing: event.target.checked })} type="checkbox" /> Editing</label>
                      <label><input checked={draft.supports_multiple_inputs} onChange={(event) => setDraft({ ...draft, supports_multiple_inputs: event.target.checked })} type="checkbox" /> Multiple inputs</label>
                      <label><input checked={draft.supports_masks} onChange={(event) => setDraft({ ...draft, supports_masks: event.target.checked })} type="checkbox" /> Masks</label>
                    </div>
                    <div className={styles.fields}>
                      <label>Default size<input value={draft.default_size} onChange={(event) => setDraft({ ...draft, default_size: event.target.value })} placeholder="1024x1024" /></label>
                      <label>Default quality<input value={draft.default_quality} onChange={(event) => setDraft({ ...draft, default_quality: event.target.value })} placeholder="high" /></label>
                      <label>Output format<select value={draft.default_output_format} onChange={(event) => setDraft({ ...draft, default_output_format: event.target.value as ProfileDraft["default_output_format"] })}><option value="png">PNG</option><option value="jpeg">JPEG</option><option value="webp">WebP</option></select></label>
                      <label>Default count<input min={1} max={4} type="number" value={draft.default_count} onChange={(event) => setDraft({ ...draft, default_count: Number(event.target.value) })} /></label>
                      <label>Max inputs<input disabled={!draft.supports_multiple_inputs} min={1} max={16} type="number" value={draft.max_input_images} onChange={(event) => setDraft({ ...draft, max_input_images: Number(event.target.value) })} /></label>
                      <label>Background<input value={draft.default_background} onChange={(event) => setDraft({ ...draft, default_background: event.target.value })} placeholder="transparent" /></label>
                      <label>Input fidelity<input value={draft.default_input_fidelity} onChange={(event) => setDraft({ ...draft, default_input_fidelity: event.target.value })} placeholder="high" /></label>
                    </div>
                    <label className={styles.jsonField}>Additional provider parameters<textarea rows={6} value={draft.provider_parameters} onChange={(event) => setDraft({ ...draft, provider_parameters: event.target.value })} /></label>
                    <div className={styles.formActions}>
                      <button onClick={() => { setEditingProfileId(null); setDraft(null); }} type="button">Cancel</button>
                      <button disabled={saving} onClick={() => void saveProfile(profile)} type="button">{saving ? "Saving…" : "Save profile"}</button>
                    </div>
                  </div>
                ) : (
                  <div className={styles.profileSummary}>
                    <span className={profile.supports_generation ? styles.enabled : ""}>Generation</span>
                    <span className={profile.supports_editing ? styles.enabled : ""}>Editing</span>
                    <span className={profile.supports_masks ? styles.enabled : ""}>Masks</span>
                    <small>{profile.default_size ?? "Provider size"} · {profile.default_quality ?? "Provider quality"} · {profile.default_output_format}</small>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
