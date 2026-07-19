"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  apiRequest,
  type CachedModel,
  type ModelEndpoint,
  type ModelPreferences,
  type ModelRouting,
} from "../../../lib/api";
import type { RetrievalPreferences } from "../../../lib/retrieval-api";
import { ModelSelect } from "./model-browser";
import {
  notifySettingsUpdated,
  SummaryCard,
  SummaryGrid,
  UnsavedBadge,
  useUnsavedChanges,
} from "../settings-primitives";
import styles from "../simple-settings.module.css";

type EndpointDraft = {
  id: string | null;
  name: string;
  baseUrl: string;
  apiKey: string;
  enabled: boolean;
};

type RoleDraft = {
  primaryModelId: string;
  utilityModelId: string;
  imageModelId: string;
  embeddingModelId: string;
};

const blankEndpoint: EndpointDraft = {
  id: null,
  name: "",
  baseUrl: "",
  apiKey: "",
  enabled: true,
};

function roleDraft(
  preferences: ModelPreferences | null,
  retrievalPreferences: RetrievalPreferences,
): RoleDraft {
  return {
    primaryModelId: preferences?.primary?.id ?? "",
    utilityModelId: preferences?.utility?.id ?? "",
    imageModelId: preferences?.image?.id ?? "",
    embeddingModelId: retrievalPreferences.embedding_model?.id ?? "",
  };
}

function endpointDraft(item: ModelEndpoint): EndpointDraft {
  return {
    id: item.id,
    name: item.name,
    baseUrl: item.base_url,
    apiKey: "",
    enabled: item.enabled,
  };
}

function sameRoles(left: RoleDraft, right: RoleDraft): boolean {
  return (
    left.primaryModelId === right.primaryModelId &&
    left.utilityModelId === right.utilityModelId &&
    left.imageModelId === right.imageModelId &&
    left.embeddingModelId === right.embeddingModelId
  );
}

function formatDate(value: string | null): string {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function SimpleModelSettings({
  initialEndpoints,
  initialModels,
  initialPreferences,
  initialRetrievalPreferences,
  initialRouting,
  initialError,
}: {
  initialEndpoints: ModelEndpoint[];
  initialModels: CachedModel[];
  initialPreferences: ModelPreferences | null;
  initialRetrievalPreferences: RetrievalPreferences;
  initialRouting: ModelRouting;
  initialError: string | null;
}) {
  const router = useRouter();
  const [endpoints, setEndpoints] = useState(initialEndpoints);
  const [models, setModels] = useState(initialModels);
  const [preferences, setPreferences] = useState(initialPreferences);
  const [retrievalPreferences, setRetrievalPreferences] = useState(
    initialRetrievalPreferences,
  );
  const [roles, setRoles] = useState(() =>
    roleDraft(initialPreferences, initialRetrievalPreferences),
  );
  const [savedRoles, setSavedRoles] = useState(() =>
    roleDraft(initialPreferences, initialRetrievalPreferences),
  );
  const [endpoint, setEndpoint] = useState<EndpointDraft>(blankEndpoint);
  const [fallbackIds, setFallbackIds] = useState(
    initialRouting.fallbacks.map((item) => item.id),
  );
  const [savedFallbackIds, setSavedFallbackIds] = useState(
    initialRouting.fallbacks.map((item) => item.id),
  );
  const [fallbackCandidate, setFallbackCandidate] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);

  const enabledEndpointIds = useMemo(
    () => new Set(endpoints.filter((item) => item.enabled).map((item) => item.id)),
    [endpoints],
  );
  const selectableModels = useMemo(
    () => models.filter((model) => enabledEndpointIds.has(model.endpoint_id)),
    [enabledEndpointIds, models],
  );
  const fallbackCandidates = useMemo(
    () =>
      selectableModels.filter(
        (model) => model.id !== roles.primaryModelId && !fallbackIds.includes(model.id),
      ),
    [fallbackIds, roles.primaryModelId, selectableModels],
  );
  const fallbackEntries = fallbackIds
    .map((id) => models.find((model) => model.id === id))
    .filter((model): model is CachedModel => Boolean(model));
  const roleDirty = !sameRoles(roles, savedRoles);
  const fallbackDirty = fallbackIds.join("|") !== savedFallbackIds.join("|");
  const endpointDirty = endpoint.id
    ? (() => {
        const original = endpoints.find((item) => item.id === endpoint.id);
        return (
          !original ||
          endpoint.name !== original.name ||
          endpoint.baseUrl !== original.base_url ||
          endpoint.enabled !== original.enabled ||
          Boolean(endpoint.apiKey)
        );
      })()
    : Boolean(endpoint.name || endpoint.baseUrl || endpoint.apiKey || !endpoint.enabled);

  useUnsavedChanges(roleDirty || fallbackDirty || endpointDirty);

  async function refresh() {
    const [nextEndpoints, nextModels, nextPreferences, nextRetrievalPreferences, nextRouting] =
      await Promise.all([
        apiRequest<ModelEndpoint[]>("/api/model-endpoints"),
        apiRequest<CachedModel[]>("/api/models"),
        apiRequest<ModelPreferences>("/api/model-preferences"),
        apiRequest<RetrievalPreferences>("/api/retrieval-preferences"),
        apiRequest<ModelRouting>("/api/model-routing"),
      ]);
    const nextRoles = roleDraft(nextPreferences, nextRetrievalPreferences);
    const nextFallbackIds = nextRouting.fallbacks.map((item) => item.id);
    setEndpoints(nextEndpoints);
    setModels(nextModels);
    setPreferences(nextPreferences);
    setRetrievalPreferences(nextRetrievalPreferences);
    setRoles(nextRoles);
    setSavedRoles(nextRoles);
    setFallbackIds(nextFallbackIds);
    setSavedFallbackIds(nextFallbackIds);
  }

  async function run(key: string, operation: () => Promise<void>) {
    if (busy) return;
    setBusy(key);
    setNotice(null);
    setError(null);
    try {
      await operation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The operation failed.");
      await refresh().catch(() => undefined);
    } finally {
      setBusy(null);
    }
  }

  function completeUpdate(message: string) {
    setNotice(message);
    notifySettingsUpdated();
    router.refresh();
  }

  async function saveEndpoint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await run("endpoint-save", async () => {
      const payload = {
        name: endpoint.name.trim(),
        base_url: endpoint.baseUrl.trim(),
        enabled: endpoint.enabled,
        ...(endpoint.apiKey ? { api_key: endpoint.apiKey } : {}),
      };
      await apiRequest(
        endpoint.id ? `/api/model-endpoints/${endpoint.id}` : "/api/model-endpoints",
        {
          method: endpoint.id ? "PATCH" : "POST",
          body: JSON.stringify(payload),
        },
      );
      setEndpoint(blankEndpoint);
      await refresh();
      completeUpdate(endpoint.id ? "Endpoint updated." : "Endpoint added.");
    });
  }

  async function endpointAction(item: ModelEndpoint, action: "test" | "sync") {
    await run(`${action}:${item.id}`, async () => {
      const result = await apiRequest<{ message?: string; models_found?: number }>(
        `/api/model-endpoints/${item.id}/${action}`,
        { method: "POST" },
      );
      await refresh();
      completeUpdate(
        result.message ??
          (action === "sync"
            ? `Model cache updated. ${result.models_found ?? 0} models found.`
            : `${item.name} is reachable.`),
      );
    });
  }

  async function saveRoles(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await run("roles-save", async () => {
      const nextPreferences = await apiRequest<ModelPreferences>("/api/model-preferences", {
        method: "PUT",
        body: JSON.stringify({
          primary_model_id: roles.primaryModelId || null,
          utility_model_id: roles.utilityModelId || null,
          image_model_id: roles.imageModelId || null,
        }),
      });
      const nextRetrievalPreferences = await apiRequest<RetrievalPreferences>(
        "/api/retrieval-preferences",
        {
          method: "PUT",
          body: JSON.stringify({ embedding_model_id: roles.embeddingModelId || null }),
        },
      );
      const nextRoles = roleDraft(nextPreferences, nextRetrievalPreferences);
      setPreferences(nextPreferences);
      setRetrievalPreferences(nextRetrievalPreferences);
      setRoles(nextRoles);
      setSavedRoles(nextRoles);
      completeUpdate("Default model roles saved.");
    });
  }

  function addFallback() {
    if (!fallbackCandidate || fallbackIds.includes(fallbackCandidate)) return;
    setFallbackIds((current) => [...current, fallbackCandidate]);
    setFallbackCandidate("");
  }

  function moveFallback(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= fallbackIds.length) return;
    setFallbackIds((current) => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function saveFallbacks() {
    await run("fallback-save", async () => {
      const saved = await apiRequest<ModelRouting>("/api/model-routing", {
        method: "PUT",
        body: JSON.stringify({ fallback_model_ids: fallbackIds }),
      });
      const next = saved.fallbacks.map((item) => item.id);
      setFallbackIds(next);
      setSavedFallbackIds(next);
      completeUpdate("Fallback order saved.");
    });
  }

  return (
    <div aria-busy={busy !== null} className={styles.root}>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}
      {!error && notice ? <div className={styles.notice} role="status">{notice}</div> : null}

      <SummaryGrid>
        <SummaryCard
          label="Endpoints"
          value={`${endpoints.filter((item) => item.enabled).length}/${endpoints.length} enabled`}
          note={`${models.length} cached models`}
        />
        <SummaryCard
          label="Primary"
          value={preferences?.primary?.model_id ?? "Not configured"}
          note={preferences?.primary?.endpoint_name}
        />
        <SummaryCard
          label="Utility"
          value={preferences?.resolved_utility?.model_id ?? "Not configured"}
          note={preferences?.utility ? "Explicit" : "Inherits primary"}
        />
        <SummaryCard
          label="Image"
          value={preferences?.image?.model_id ?? "Disabled"}
          note={preferences?.image?.endpoint_name}
        />
        <SummaryCard
          label="Embedding"
          value={retrievalPreferences.embedding_model?.model_id ?? "Lexical only"}
          note={retrievalPreferences.embedding_model?.endpoint_name}
        />
      </SummaryGrid>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Default models</h2>
            <p>Choose the models Aster uses day to day. Empty optional roles inherit or stay disabled.</p>
          </div>
          <UnsavedBadge visible={roleDirty} />
        </div>
        <form className={styles.sectionBody} onSubmit={saveRoles}>
          <div className={styles.formGrid}>
            <ModelSelect
              disabled={busy !== null}
              emptyLabel="Not configured"
              label="Primary model"
              models={selectableModels}
              onChange={(value) => setRoles({ ...roles, primaryModelId: value })}
              value={roles.primaryModelId}
            />
            <ModelSelect
              disabled={busy !== null}
              emptyLabel="Use primary model"
              label="Utility model"
              models={selectableModels}
              onChange={(value) => setRoles({ ...roles, utilityModelId: value })}
              value={roles.utilityModelId}
            />
            <ModelSelect
              disabled={busy !== null}
              emptyLabel="Disabled"
              label="Image model"
              models={selectableModels}
              onChange={(value) => setRoles({ ...roles, imageModelId: value })}
              value={roles.imageModelId}
            />
            <ModelSelect
              disabled={busy !== null}
              emptyLabel="Lexical retrieval only"
              label="Embedding model"
              models={selectableModels}
              onChange={(value) => setRoles({ ...roles, embeddingModelId: value })}
              value={roles.embeddingModelId}
            />
          </div>
          <div className={styles.actions}>
            <button
              className={styles.primaryButton}
              disabled={busy !== null || !roleDirty}
              type="submit"
            >
              {busy === "roles-save" ? "Saving defaults" : "Save defaults"}
            </button>
          </div>
        </form>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Fallback order</h2>
            <p>Used only when the primary route cannot complete a compatible chat request.</p>
          </div>
          <UnsavedBadge visible={fallbackDirty} />
        </div>
        <div className={styles.sectionBody}>
          <div className={styles.inlineControl}>
            <select
              aria-label="Fallback model to add"
              disabled={busy !== null || fallbackCandidates.length === 0}
              onChange={(event) => setFallbackCandidate(event.target.value)}
              value={fallbackCandidate}
            >
              <option value="">Choose a fallback</option>
              {fallbackCandidates.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.endpoint_name} / {model.model_id}
                </option>
              ))}
            </select>
            <button
              className={styles.secondaryButton}
              disabled={!fallbackCandidate || busy !== null}
              onClick={addFallback}
              type="button"
            >
              Add
            </button>
          </div>
          <div className={styles.list}>
            {fallbackEntries.length === 0 ? (
              <div className={styles.empty}>No fallback models configured.</div>
            ) : (
              fallbackEntries.map((model, index) => (
                <article className={styles.row} key={model.id}>
                  <div className={styles.rowMain}>
                    <strong>{model.model_id}</strong>
                    <small>{model.endpoint_name}</small>
                  </div>
                  <div className={styles.rowActions}>
                    <button
                      aria-label={`Move ${model.model_id} up`}
                      className={styles.iconButton}
                      disabled={busy !== null || index === 0}
                      onClick={() => moveFallback(index, -1)}
                      type="button"
                    >
                      ↑
                    </button>
                    <button
                      aria-label={`Move ${model.model_id} down`}
                      className={styles.iconButton}
                      disabled={busy !== null || index === fallbackEntries.length - 1}
                      onClick={() => moveFallback(index, 1)}
                      type="button"
                    >
                      ↓
                    </button>
                    <button
                      className={styles.dangerButton}
                      disabled={busy !== null}
                      onClick={() => setFallbackIds((current) => current.filter((id) => id !== model.id))}
                      type="button"
                    >
                      Remove
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
          <div className={styles.actions}>
            <button
              className={styles.primaryButton}
              disabled={busy !== null || !fallbackDirty}
              onClick={() => void saveFallbacks()}
              type="button"
            >
              {busy === "fallback-save" ? "Saving order" : "Save fallback order"}
            </button>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Endpoints</h2>
            <p>Add a compatible API or maintain the connections already in use.</p>
          </div>
          <UnsavedBadge visible={endpointDirty} />
        </div>
        <div className={styles.sectionBody}>
          <form className={styles.formGrid} onSubmit={saveEndpoint}>
            <label className={styles.field}>
              <span>Name</span>
              <input
                disabled={busy !== null}
                maxLength={120}
                onChange={(event) => setEndpoint({ ...endpoint, name: event.target.value })}
                placeholder="Local API"
                required
                value={endpoint.name}
              />
            </label>
            <label className={styles.field}>
              <span>Base URL</span>
              <input
                disabled={busy !== null}
                onChange={(event) => setEndpoint({ ...endpoint, baseUrl: event.target.value })}
                placeholder="https://example.com/v1"
                required
                type="url"
                value={endpoint.baseUrl}
              />
            </label>
            <label className={styles.wideField}>
              <span>API key</span>
              <input
                autoComplete="new-password"
                disabled={busy !== null}
                onChange={(event) => setEndpoint({ ...endpoint, apiKey: event.target.value })}
                placeholder={endpoint.id ? "Leave blank to keep the stored key" : "Optional"}
                type="password"
                value={endpoint.apiKey}
              />
            </label>
            <label className={styles.checkboxField}>
              <input
                checked={endpoint.enabled}
                disabled={busy !== null}
                onChange={(event) => setEndpoint({ ...endpoint, enabled: event.target.checked })}
                type="checkbox"
              />
              Endpoint enabled
            </label>
            <div className={styles.actions}>
              {endpoint.id || endpointDirty ? (
                <button
                  className={styles.secondaryButton}
                  disabled={busy !== null}
                  onClick={() => setEndpoint(blankEndpoint)}
                  type="button"
                >
                  Cancel
                </button>
              ) : null}
              <button className={styles.primaryButton} disabled={busy !== null} type="submit">
                {busy === "endpoint-save"
                  ? "Saving endpoint"
                  : endpoint.id
                    ? "Save endpoint"
                    : "Add endpoint"}
              </button>
            </div>
          </form>

          <div className={styles.list}>
            {endpoints.length === 0 ? (
              <div className={styles.empty}>Add an OpenAI-compatible endpoint to continue.</div>
            ) : (
              endpoints.map((item) => (
                <article className={styles.row} key={item.id}>
                  <div className={styles.rowMain}>
                    <div className={styles.badges}>
                      <span className={`${styles.badge} ${item.enabled ? styles.successBadge : ""}`}>
                        {item.enabled ? "Enabled" : "Disabled"}
                      </span>
                      <span className={styles.badge}>{item.cached_model_count} models</span>
                      <span className={styles.badge}>
                        {item.has_api_key ? "Key stored" : "No key"}
                      </span>
                    </div>
                    <strong>{item.name}</strong>
                    <p>{item.base_url}</p>
                    <small>
                      Last sync: {formatDate(item.last_successful_sync_at)}
                      {item.last_sync_error ? ` · ${item.last_sync_error}` : ""}
                    </small>
                  </div>
                  <div className={styles.rowActions}>
                    <button
                      className={styles.secondaryButton}
                      disabled={busy !== null}
                      onClick={() => setEndpoint(endpointDraft(item))}
                      type="button"
                    >
                      Edit
                    </button>
                    <button
                      className={styles.secondaryButton}
                      disabled={busy !== null}
                      onClick={() => void endpointAction(item, "test")}
                      type="button"
                    >
                      {busy === `test:${item.id}` ? "Testing" : "Test"}
                    </button>
                    <button
                      className={styles.secondaryButton}
                      disabled={busy !== null}
                      onClick={() => void endpointAction(item, "sync")}
                      type="button"
                    >
                      {busy === `sync:${item.id}` ? "Refreshing" : "Refresh models"}
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
