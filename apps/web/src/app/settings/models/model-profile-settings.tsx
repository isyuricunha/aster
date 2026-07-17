"use client";

import { useMemo, useState, type FormEvent } from "react";

import {
  apiRequest,
  type CachedModel,
  type ModelPreferences,
  type ModelProfile,
  type ModelRouting,
} from "../../../lib/api";
import { ModelSelect } from "./model-browser";
import styles from "./model-profile-settings.module.css";

type ReasoningEffortDraft = "" | "minimal" | "low" | "medium" | "high" | "xhigh";

type ProfileDraft = {
  displayName: string;
  contextWindow: string;
  maxOutputTokens: string;
  tokenParameter: ModelProfile["token_parameter"];
  temperature: string;
  topP: string;
  reasoningEffort: ReasoningEffortDraft;
  supportsChat: boolean;
  supportsStreaming: boolean;
};

const emptyProfile: ProfileDraft = {
  displayName: "",
  contextWindow: "",
  maxOutputTokens: "",
  tokenParameter: "max_tokens",
  temperature: "",
  topP: "",
  reasoningEffort: "",
  supportsChat: true,
  supportsStreaming: true,
};

function profileDraft(profile: ModelProfile): ProfileDraft {
  return {
    displayName: profile.display_name ?? "",
    contextWindow: profile.context_window?.toString() ?? "",
    maxOutputTokens: profile.max_output_tokens?.toString() ?? "",
    tokenParameter: profile.token_parameter,
    temperature: profile.temperature?.toString() ?? "",
    topP: profile.top_p?.toString() ?? "",
    reasoningEffort: profile.reasoning_effort ?? "",
    supportsChat: profile.supports_chat,
    supportsStreaming: profile.supports_streaming,
  };
}

function nullableNumber(value: string): number | null {
  const normalized = value.trim();
  return normalized ? Number(normalized) : null;
}

export function ModelProfileSettings({
  models,
  preferences,
  initialRouting,
}: {
  models: CachedModel[];
  preferences: ModelPreferences | null;
  initialRouting: ModelRouting;
}) {
  const [selectedModelId, setSelectedModelId] = useState("");
  const [profile, setProfile] = useState<ProfileDraft>(emptyProfile);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [fallbackIds, setFallbackIds] = useState(initialRouting.fallbacks.map((item) => item.id));
  const [fallbackCandidate, setFallbackCandidate] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectableModels = useMemo(
    () => models.filter((model) => model.is_available),
    [models],
  );
  const fallbackModels = useMemo(
    () => selectableModels.filter((model) => model.id !== preferences?.primary?.id),
    [preferences?.primary?.id, selectableModels],
  );
  const fallbackEntries = fallbackIds
    .map((id) => models.find((model) => model.id === id))
    .filter((model): model is CachedModel => Boolean(model));

  async function run(name: string, operation: () => Promise<void>) {
    setBusy(name);
    setNotice(null);
    setError(null);
    try {
      await operation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The operation failed.");
    } finally {
      setBusy(null);
    }
  }

  async function selectProfile(modelId: string) {
    setSelectedModelId(modelId);
    setProfileLoaded(false);
    setNotice(null);
    setError(null);
    if (!modelId) {
      setProfile(emptyProfile);
      return;
    }
    await run("load-profile", async () => {
      const loaded = await apiRequest<ModelProfile>(`/api/model-profiles/${modelId}`);
      setProfile(profileDraft(loaded));
      setProfileLoaded(true);
    });
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedModelId) return;
    await run("save-profile", async () => {
      const saved = await apiRequest<ModelProfile>(`/api/model-profiles/${selectedModelId}`, {
        method: "PUT",
        body: JSON.stringify({
          display_name: profile.displayName || null,
          context_window: nullableNumber(profile.contextWindow),
          max_output_tokens: nullableNumber(profile.maxOutputTokens),
          token_parameter: profile.tokenParameter,
          temperature: nullableNumber(profile.temperature),
          top_p: nullableNumber(profile.topP),
          reasoning_effort: profile.reasoningEffort || null,
          supports_chat: profile.supportsChat,
          supports_streaming: profile.supportsStreaming,
        }),
      });
      setProfile(profileDraft(saved));
      setProfileLoaded(true);
      setNotice("Model profile saved.");
    });
  }

  async function resetProfile() {
    if (!selectedModelId) return;
    await run("reset-profile", async () => {
      await apiRequest(`/api/model-profiles/${selectedModelId}`, { method: "DELETE" });
      const defaults = await apiRequest<ModelProfile>(`/api/model-profiles/${selectedModelId}`);
      setProfile(profileDraft(defaults));
      setProfileLoaded(true);
      setNotice("Model profile reset to provider defaults.");
    });
  }

  function addFallback() {
    if (!fallbackCandidate || fallbackIds.includes(fallbackCandidate)) return;
    setFallbackIds((current) => [...current, fallbackCandidate]);
    setFallbackCandidate("");
  }

  function moveFallback(index: number, direction: -1 | 1) {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= fallbackIds.length) return;
    setFallbackIds((current) => {
      const next = [...current];
      [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
      return next;
    });
  }

  async function saveFallbacks() {
    await run("save-fallbacks", async () => {
      const saved = await apiRequest<ModelRouting>("/api/model-routing", {
        method: "PUT",
        body: JSON.stringify({ fallback_model_ids: fallbackIds }),
      });
      setFallbackIds(saved.fallbacks.map((item) => item.id));
      setNotice("Fallback order saved.");
    });
  }

  return (
    <div className={styles.stack}>
      {(notice || error) && (
        <div className={`banner ${error ? "banner-error" : "banner-success"}`} role="status">
          {error ?? notice}
        </div>
      )}

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Generation</p>
            <h2>Model profiles</h2>
            <p className="section-copy">
              Keep provider defaults by leaving values empty. Aster sends only explicitly configured
              parameters.
            </p>
          </div>
        </div>

        <ModelSelect
          label="Model to configure"
          emptyLabel="Choose a model"
          models={models}
          value={selectedModelId}
          onChange={(value) => void selectProfile(value)}
        />

        {selectedModelId && profileLoaded && (
          <form className={`form-grid ${styles.profileForm}`} onSubmit={saveProfile}>
            <label className="form-span-two">
              <span>Display name</span>
              <input
                maxLength={120}
                placeholder="Optional local label"
                value={profile.displayName}
                onChange={(event) => setProfile({ ...profile, displayName: event.target.value })}
              />
            </label>
            <label>
              <span>Context window</span>
              <input
                min={1}
                type="number"
                placeholder="Provider default"
                value={profile.contextWindow}
                onChange={(event) => setProfile({ ...profile, contextWindow: event.target.value })}
              />
            </label>
            <label>
              <span>Maximum output tokens</span>
              <input
                min={1}
                type="number"
                placeholder="Provider default"
                value={profile.maxOutputTokens}
                onChange={(event) => setProfile({ ...profile, maxOutputTokens: event.target.value })}
              />
            </label>
            <label>
              <span>Output token parameter</span>
              <select
                value={profile.tokenParameter}
                onChange={(event) =>
                  setProfile({
                    ...profile,
                    tokenParameter: event.target.value as ProfileDraft["tokenParameter"],
                  })
                }
              >
                <option value="max_tokens">max_tokens</option>
                <option value="max_completion_tokens">max_completion_tokens</option>
                <option value="none">Do not send a token limit</option>
              </select>
            </label>
            <label>
              <span>Reasoning effort</span>
              <select
                value={profile.reasoningEffort}
                onChange={(event) =>
                  setProfile({
                    ...profile,
                    reasoningEffort: event.target.value as ReasoningEffortDraft,
                  })
                }
              >
                <option value="">Provider default</option>
                <option value="minimal">Minimal</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="xhigh">Extra high</option>
              </select>
            </label>
            <label>
              <span>Temperature</span>
              <input
                max={2}
                min={0}
                step="0.01"
                type="number"
                placeholder="Provider default"
                value={profile.temperature}
                onChange={(event) => setProfile({ ...profile, temperature: event.target.value })}
              />
            </label>
            <label>
              <span>Top P</span>
              <input
                max={1}
                min={0.01}
                step="0.01"
                type="number"
                placeholder="Provider default"
                value={profile.topP}
                onChange={(event) => setProfile({ ...profile, topP: event.target.value })}
              />
            </label>
            <label className="checkbox-row">
              <input
                checked={profile.supportsChat}
                type="checkbox"
                onChange={(event) =>
                  setProfile({
                    ...profile,
                    supportsChat: event.target.checked,
                    supportsStreaming: event.target.checked && profile.supportsStreaming,
                  })
                }
              />
              <span>Supports chat completions</span>
            </label>
            <label className="checkbox-row">
              <input
                checked={profile.supportsStreaming}
                disabled={!profile.supportsChat}
                type="checkbox"
                onChange={(event) =>
                  setProfile({ ...profile, supportsStreaming: event.target.checked })
                }
              />
              <span>Supports streaming</span>
            </label>
            <div className="form-actions form-span-two">
              <button className="button" disabled={busy === "save-profile"} type="submit">
                Save profile
              </button>
              <button
                className="button button-secondary"
                disabled={busy === "reset-profile"}
                onClick={() => void resetProfile()}
                type="button"
              >
                Reset defaults
              </button>
            </div>
          </form>
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Reliability</p>
            <h2>Chat fallback order</h2>
            <p className="section-copy">
              Primary is always attempted first. Fallbacks are used only before the first response token.
            </p>
          </div>
        </div>

        <div className={styles.fallbackPicker}>
          <ModelSelect
            label="Add fallback model"
            emptyLabel="Choose a fallback"
            models={fallbackModels}
            value={fallbackCandidate}
            onChange={setFallbackCandidate}
          />
          <button
            className="button button-secondary"
            disabled={!fallbackCandidate || fallbackIds.includes(fallbackCandidate)}
            onClick={addFallback}
            type="button"
          >
            Add fallback
          </button>
        </div>

        {fallbackEntries.length === 0 ? (
          <div className="empty-state">No fallback models configured.</div>
        ) : (
          <ol className={styles.fallbackList}>
            {fallbackEntries.map((model, index) => (
              <li key={model.id}>
                <span className={styles.position}>{index + 1}</span>
                <div>
                  <strong>{model.model_id}</strong>
                  <small>{model.endpoint_name}</small>
                </div>
                <div className={styles.fallbackActions}>
                  <button
                    aria-label="Move fallback up"
                    disabled={index === 0}
                    onClick={() => moveFallback(index, -1)}
                    type="button"
                  >
                    ↑
                  </button>
                  <button
                    aria-label="Move fallback down"
                    disabled={index === fallbackEntries.length - 1}
                    onClick={() => moveFallback(index, 1)}
                    type="button"
                  >
                    ↓
                  </button>
                  <button
                    aria-label="Remove fallback"
                    className={styles.remove}
                    onClick={() =>
                      setFallbackIds((current) => current.filter((id) => id !== model.id))
                    }
                    type="button"
                  >
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ol>
        )}

        <div className="form-actions">
          <button
            className="button"
            disabled={busy === "save-fallbacks"}
            onClick={() => void saveFallbacks()}
            type="button"
          >
            Save fallback order
          </button>
        </div>
      </section>
    </div>
  );
}
