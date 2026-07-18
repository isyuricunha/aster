"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";

import {
  apiRequest,
  type CachedModel,
  type ModelEndpoint,
  type ModelPreferences,
} from "../../../lib/api";
import { EndpointModelList, ModelSelect } from "./model-browser";
import styles from "./model-settings.module.css";

type EndpointDraft = {
  id: string | null;
  name: string;
  baseUrl: string;
  apiKey: string;
  enabled: boolean;
};

type PreferenceDraft = {
  primaryModelId: string;
  utilityModelId: string;
  imageModelId: string;
};

const emptyEndpoint: EndpointDraft = {
  id: null,
  name: "",
  baseUrl: "",
  apiKey: "",
  enabled: true,
};

function preferenceDraft(preferences: ModelPreferences | null): PreferenceDraft {
  return {
    primaryModelId: preferences?.primary?.id ?? "",
    utilityModelId: preferences?.utility?.id ?? "",
    imageModelId: preferences?.image?.id ?? "",
  };
}

function formatDate(value: string | null): string {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ModelSettings({
  initialEndpoints,
  initialModels,
  initialPreferences,
  initialError,
}: {
  initialEndpoints: ModelEndpoint[];
  initialModels: CachedModel[];
  initialPreferences: ModelPreferences | null;
  initialError: string | null;
}) {
  const [endpoints, setEndpoints] = useState(initialEndpoints);
  const [models, setModels] = useState(initialModels);
  const [preferences, setPreferences] = useState(initialPreferences);
  const [roles, setRoles] = useState(() => preferenceDraft(initialPreferences));
  const [endpoint, setEndpoint] = useState<EndpointDraft>(emptyEndpoint);
  const [manualIds, setManualIds] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);

  const refresh = useCallback(async () => {
    const [nextEndpoints, nextModels, nextPreferences] = await Promise.all([
      apiRequest<ModelEndpoint[]>("/api/model-endpoints"),
      apiRequest<CachedModel[]>("/api/models"),
      apiRequest<ModelPreferences>("/api/model-preferences"),
    ]);
    setEndpoints(nextEndpoints);
    setModels(nextModels);
    setPreferences(nextPreferences);
    setRoles(preferenceDraft(nextPreferences));
  }, []);

  const selectableModels = useMemo(() => {
    const enabled = new Set(endpoints.filter((item) => item.enabled).map((item) => item.id));
    return models.filter((model) => enabled.has(model.endpoint_id));
  }, [endpoints, models]);

  const modelsByEndpoint = useMemo(() => {
    const grouped = new Map<string, CachedModel[]>();
    for (const model of models) {
      const cached = grouped.get(model.endpoint_id);
      if (cached) {
        cached.push(model);
      } else {
        grouped.set(model.endpoint_id, [model]);
      }
    }
    return grouped;
  }, [models]);

  async function run(name: string, operation: () => Promise<void>) {
    if (busy) return;
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

  async function saveEndpoint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await run("save-endpoint", async () => {
      const payload = {
        name: endpoint.name,
        base_url: endpoint.baseUrl,
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
      setEndpoint(emptyEndpoint);
      setNotice(endpoint.id ? "Endpoint updated." : "Endpoint added.");
      await refresh();
    });
  }

  async function endpointAction(item: ModelEndpoint, action: "test" | "sync" | "delete") {
    if (action === "delete" && !window.confirm(`Delete ${item.name} and its cached models?`)) return;
    await run(`${action}-${item.id}`, async () => {
      if (action === "delete") {
        await apiRequest(`/api/model-endpoints/${item.id}`, { method: "DELETE" });
        setNotice("Endpoint deleted.");
      } else {
        const result = await apiRequest<{ message?: string; models_found?: number }>(
          `/api/model-endpoints/${item.id}/${action}`,
          { method: "POST" },
        );
        setNotice(
          result.message ?? `Model cache updated. ${result.models_found ?? 0} models found.`,
        );
      }
      await refresh();
    });
  }

  async function addManualModel(item: ModelEndpoint) {
    const modelId = manualIds[item.id]?.trim();
    if (!modelId) {
      setError("Enter a model ID first.");
      return;
    }
    await run(`manual-${item.id}`, async () => {
      await apiRequest(`/api/model-endpoints/${item.id}/models`, {
        method: "POST",
        body: JSON.stringify({ model_id: modelId }),
      });
      setManualIds((current) => ({ ...current, [item.id]: "" }));
      setNotice(`Added ${modelId} to the local model cache.`);
      await refresh();
    });
  }

  async function saveRoles(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await run("save-roles", async () => {
      const next = await apiRequest<ModelPreferences>("/api/model-preferences", {
        method: "PUT",
        body: JSON.stringify({
          primary_model_id: roles.primaryModelId || null,
          utility_model_id: roles.utilityModelId || null,
          image_model_id: roles.imageModelId || null,
        }),
      });
      setPreferences(next);
      setRoles(preferenceDraft(next));
      setNotice("Default models saved.");
    });
  }

  return (
    <div aria-busy={busy !== null} className={`settings-stack ${styles.root}`}>
      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}
      {!error && notice && (
        <div className="banner banner-success" role="status">
          {notice}
        </div>
      )}

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Connection</p>
            <h2>{endpoint.id ? "Edit endpoint" : "Add endpoint"}</h2>
          </div>
          {endpoint.id && (
            <button
              className="button button-secondary"
              disabled={busy !== null}
              onClick={() => setEndpoint(emptyEndpoint)}
              type="button"
            >
              Cancel edit
            </button>
          )}
        </div>
        <form
          aria-busy={busy === "save-endpoint"}
          className="form-grid"
          onSubmit={saveEndpoint}
        >
          <Field label="Name">
            <input
              disabled={busy !== null}
              required
              value={endpoint.name}
              onChange={(event) => setEndpoint({ ...endpoint, name: event.target.value })}
              placeholder="Local API"
            />
          </Field>
          <Field label="Base URL">
            <input
              disabled={busy !== null}
              required
              type="url"
              value={endpoint.baseUrl}
              onChange={(event) => setEndpoint({ ...endpoint, baseUrl: event.target.value })}
              placeholder="https://example.com/v1"
            />
          </Field>
          <Field className="form-span-two" label="API key">
            <input
              type="password"
              autoComplete="new-password"
              disabled={busy !== null}
              value={endpoint.apiKey}
              onChange={(event) => setEndpoint({ ...endpoint, apiKey: event.target.value })}
              placeholder={endpoint.id ? "Leave blank to keep the current key" : "Optional"}
            />
          </Field>
          <label className="checkbox-row form-span-two">
            <input
              type="checkbox"
              checked={endpoint.enabled}
              disabled={busy !== null}
              onChange={(event) => setEndpoint({ ...endpoint, enabled: event.target.checked })}
            />
            <span>Endpoint enabled</span>
          </label>
          <div className="form-actions form-span-two">
            <button className="button" disabled={busy !== null} type="submit">
              {busy === "save-endpoint"
                ? endpoint.id
                  ? "Saving endpoint"
                  : "Adding endpoint"
                : endpoint.id
                  ? "Save endpoint"
                  : "Add endpoint"}
            </button>
          </div>
        </form>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Connections</p>
            <h2>Configured endpoints</h2>
          </div>
          <span aria-label={`${endpoints.length} configured endpoints`} className="count">
            {endpoints.length}
          </span>
        </div>
        {endpoints.length === 0 ? (
          <div className="empty-state" role="status">
            Add an OpenAI-compatible endpoint to continue.
          </div>
        ) : (
          <div className="endpoint-list">
            {endpoints.map((item) => {
              const cached = modelsByEndpoint.get(item.id) ?? [];
              const endpointHeadingId = `endpoint-${item.id}-heading`;
              const endpointBusy = busy?.endsWith(`-${item.id}`) ?? false;
              return (
                <article
                  aria-busy={endpointBusy}
                  aria-labelledby={endpointHeadingId}
                  className="endpoint-card"
                  key={item.id}
                >
                  <div className="endpoint-header">
                    <div>
                      <div className="title-row">
                        <h3 id={endpointHeadingId}>{item.name}</h3>
                        <span className={`pill ${item.enabled ? "pill-success" : ""}`}>
                          {item.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                      <code>{item.base_url}</code>
                    </div>
                    <div className="button-row">
                      <button
                        aria-label={`Edit endpoint ${item.name}`}
                        className="button button-secondary"
                        disabled={busy !== null}
                        onClick={() =>
                          setEndpoint({
                            id: item.id,
                            name: item.name,
                            baseUrl: item.base_url,
                            apiKey: "",
                            enabled: item.enabled,
                          })
                        }
                        type="button"
                      >
                        Edit
                      </button>
                      <button
                        aria-label={`Delete endpoint ${item.name} and its cached models`}
                        className="button button-danger"
                        disabled={busy !== null}
                        onClick={() => void endpointAction(item, "delete")}
                        type="button"
                      >
                        {busy === `delete-${item.id}` ? "Deleting" : "Delete"}
                      </button>
                    </div>
                  </div>
                  <dl className="endpoint-meta">
                    <Meta label="API key" value={item.has_api_key ? "Stored securely" : "Not set"} />
                    <Meta label="Cached models" value={String(item.cached_model_count)} />
                    <Meta
                      label="Last successful sync"
                      value={formatDate(item.last_successful_sync_at)}
                    />
                    <Meta label="Status" value={item.last_sync_status ?? "Not synchronized"} />
                  </dl>
                  {item.last_sync_error && (
                    <p className="inline-error" role="alert">
                      {item.last_sync_error}
                    </p>
                  )}
                  <div className="button-row endpoint-actions">
                    <ActionButton
                      busy={busy === `test-${item.id}`}
                      busyLabel="Testing connection"
                      disabled={busy !== null}
                      onClick={() => endpointAction(item, "test")}
                    >
                      Test connection
                    </ActionButton>
                    <ActionButton
                      busy={busy === `sync-${item.id}`}
                      busyLabel="Refreshing models"
                      disabled={busy !== null}
                      primary
                      onClick={() => endpointAction(item, "sync")}
                    >
                      Refresh models
                    </ActionButton>
                  </div>
                  <div className="manual-model-row">
                    <input
                      aria-label={`Model ID to add to ${item.name}`}
                      disabled={busy !== null}
                      value={manualIds[item.id] ?? ""}
                      onChange={(event) =>
                        setManualIds((current) => ({ ...current, [item.id]: event.target.value }))
                      }
                      placeholder="Enter a model ID manually"
                    />
                    <ActionButton
                      busy={busy === `manual-${item.id}`}
                      busyLabel="Adding model"
                      disabled={busy !== null}
                      onClick={() => addManualModel(item)}
                    >
                      Add model
                    </ActionButton>
                  </div>
                  {cached.length > 0 && <EndpointModelList models={cached} />}
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Defaults</p>
            <h2>Model roles</h2>
            <p className="section-copy">
              Utility uses primary when empty. Image features stay disabled without an image model.
            </p>
          </div>
        </div>
        <form aria-busy={busy === "save-roles"} className="form-grid" onSubmit={saveRoles}>
          <ModelSelect
            disabled={busy !== null}
            label="Primary model"
            emptyLabel="Not configured"
            models={selectableModels}
            value={roles.primaryModelId}
            onChange={(value) => setRoles({ ...roles, primaryModelId: value })}
          />
          <ModelSelect
            disabled={busy !== null}
            label="Utility model"
            emptyLabel="Use primary model"
            models={selectableModels}
            value={roles.utilityModelId}
            onChange={(value) => setRoles({ ...roles, utilityModelId: value })}
          />
          <ModelSelect
            disabled={busy !== null}
            label="Image model"
            emptyLabel="Disabled"
            models={selectableModels}
            value={roles.imageModelId}
            onChange={(value) => setRoles({ ...roles, imageModelId: value })}
          />
          <div aria-live="polite" className="preference-summary">
            <span>Resolved utility</span>
            <strong>
              {preferences?.resolved_utility
                ? `${preferences.resolved_utility.endpoint_name} / ${preferences.resolved_utility.model_id}`
                : "Not configured"}
            </strong>
          </div>
          <div className="form-actions form-span-two">
            <button className="button" disabled={busy !== null} type="submit">
              {busy === "save-roles" ? "Saving model roles" : "Save model roles"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function Field({
  label,
  className,
  children,
}: {
  label: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <label className={className}>
      <span>{label}</span>
      {children}
    </label>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function ActionButton({
  busy,
  busyLabel,
  disabled,
  primary = false,
  onClick,
  children,
}: {
  busy: boolean;
  busyLabel: string;
  disabled: boolean;
  primary?: boolean;
  onClick: () => Promise<void>;
  children: React.ReactNode;
}) {
  return (
    <button
      aria-busy={busy}
      className={`button ${primary ? "" : "button-secondary"}`}
      disabled={disabled}
      onClick={() => void onClick()}
      type="button"
    >
      {busy ? busyLabel : children}
    </button>
  );
}
