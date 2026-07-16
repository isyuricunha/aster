"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";

import {
  apiRequest,
  type CachedModel,
  type ModelEndpoint,
  type ModelPreferences,
} from "../../../lib/api";

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
    <div className="settings-stack">
      {(notice || error) && (
        <div className={`banner ${error ? "banner-error" : "banner-success"}`} role="status">
          {error ?? notice}
        </div>
      )}

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Connection</p>
            <h2>{endpoint.id ? "Edit endpoint" : "Add endpoint"}</h2>
          </div>
          {endpoint.id && (
            <button className="button button-secondary" onClick={() => setEndpoint(emptyEndpoint)}>
              Cancel edit
            </button>
          )}
        </div>
        <form className="form-grid" onSubmit={saveEndpoint}>
          <Field label="Name">
            <input
              required
              value={endpoint.name}
              onChange={(event) => setEndpoint({ ...endpoint, name: event.target.value })}
              placeholder="Local API"
            />
          </Field>
          <Field label="Base URL">
            <input
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
              value={endpoint.apiKey}
              onChange={(event) => setEndpoint({ ...endpoint, apiKey: event.target.value })}
              placeholder={endpoint.id ? "Leave blank to keep the current key" : "Optional"}
            />
          </Field>
          <label className="checkbox-row form-span-two">
            <input
              type="checkbox"
              checked={endpoint.enabled}
              onChange={(event) => setEndpoint({ ...endpoint, enabled: event.target.checked })}
            />
            <span>Endpoint enabled</span>
          </label>
          <div className="form-actions form-span-two">
            <button className="button" disabled={busy === "save-endpoint"} type="submit">
              {endpoint.id ? "Save endpoint" : "Add endpoint"}
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
          <span className="count">{endpoints.length}</span>
        </div>
        {endpoints.length === 0 ? (
          <div className="empty-state">Add an OpenAI-compatible endpoint to continue.</div>
        ) : (
          <div className="endpoint-list">
            {endpoints.map((item) => {
              const cached = models.filter((model) => model.endpoint_id === item.id);
              return (
                <article className="endpoint-card" key={item.id}>
                  <div className="endpoint-header">
                    <div>
                      <div className="title-row">
                        <h3>{item.name}</h3>
                        <span className={`pill ${item.enabled ? "pill-success" : ""}`}>
                          {item.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                      <code>{item.base_url}</code>
                    </div>
                    <div className="button-row">
                      <button
                        className="button button-secondary"
                        onClick={() =>
                          setEndpoint({
                            id: item.id,
                            name: item.name,
                            baseUrl: item.base_url,
                            apiKey: "",
                            enabled: item.enabled,
                          })
                        }
                      >
                        Edit
                      </button>
                      <button
                        className="button button-danger"
                        disabled={busy === `delete-${item.id}`}
                        onClick={() => void endpointAction(item, "delete")}
                      >
                        Delete
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
                  {item.last_sync_error && <p className="inline-error">{item.last_sync_error}</p>}
                  <div className="button-row endpoint-actions">
                    <ActionButton
                      busy={busy === `test-${item.id}`}
                      onClick={() => endpointAction(item, "test")}
                    >
                      Test connection
                    </ActionButton>
                    <ActionButton
                      busy={busy === `sync-${item.id}`}
                      primary
                      onClick={() => endpointAction(item, "sync")}
                    >
                      Refresh models
                    </ActionButton>
                  </div>
                  <div className="manual-model-row">
                    <input
                      value={manualIds[item.id] ?? ""}
                      onChange={(event) =>
                        setManualIds((current) => ({ ...current, [item.id]: event.target.value }))
                      }
                      placeholder="Enter a model ID manually"
                    />
                    <ActionButton
                      busy={busy === `manual-${item.id}`}
                      onClick={() => addManualModel(item)}
                    >
                      Add model
                    </ActionButton>
                  </div>
                  {cached.length > 0 && (
                    <div className="model-list">
                      {cached.map((model) => (
                        <div className="model-row" key={model.id}>
                          <code>{model.model_id}</code>
                          <div className="model-badges">
                            {model.is_manual && <span className="pill">Manual</span>}
                            <span
                              className={`pill ${model.is_available ? "pill-success" : "pill-warning"}`}
                            >
                              {model.is_available ? "Available" : "Missing from latest sync"}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
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
        <form className="form-grid" onSubmit={saveRoles}>
          <ModelSelect
            label="Primary model"
            emptyLabel="Not configured"
            models={selectableModels}
            value={roles.primaryModelId}
            onChange={(value) => setRoles({ ...roles, primaryModelId: value })}
          />
          <ModelSelect
            label="Utility model"
            emptyLabel="Use primary model"
            models={selectableModels}
            value={roles.utilityModelId}
            onChange={(value) => setRoles({ ...roles, utilityModelId: value })}
          />
          <ModelSelect
            label="Image model"
            emptyLabel="Disabled"
            models={selectableModels}
            value={roles.imageModelId}
            onChange={(value) => setRoles({ ...roles, imageModelId: value })}
          />
          <div className="preference-summary">
            <span>Resolved utility</span>
            <strong>
              {preferences?.resolved_utility
                ? `${preferences.resolved_utility.endpoint_name} / ${preferences.resolved_utility.model_id}`
                : "Not configured"}
            </strong>
          </div>
          <div className="form-actions form-span-two">
            <button className="button" disabled={busy === "save-roles"} type="submit">
              Save model roles
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
  primary = false,
  onClick,
  children,
}: {
  busy: boolean;
  primary?: boolean;
  onClick: () => Promise<void>;
  children: React.ReactNode;
}) {
  return (
    <button
      className={`button ${primary ? "" : "button-secondary"}`}
      disabled={busy}
      onClick={() => void onClick()}
    >
      {children}
    </button>
  );
}

function ModelSelect({
  label,
  emptyLabel,
  models,
  value,
  onChange,
}: {
  label: string;
  emptyLabel: string;
  models: CachedModel[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Field label={label}>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">{emptyLabel}</option>
        {models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.endpoint_name} / {model.model_id}
            {model.is_available ? "" : " (cached)"}
          </option>
        ))}
      </select>
    </Field>
  );
}
