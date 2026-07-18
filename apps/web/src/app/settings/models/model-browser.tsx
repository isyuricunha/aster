"use client";

import { useId, useMemo, useState } from "react";

import type { CachedModel } from "../../../lib/api";
import styles from "./model-browser.module.css";

const MODEL_PAGE_SIZE = 50;
const MODEL_SELECT_LIMIT = 100;

function modelLabel(model: CachedModel): string {
  return `${model.endpoint_name} / ${model.model_id}`;
}

export function EndpointModelList({ models }: { models: CachedModel[] }) {
  const [query, setQuery] = useState("");
  const [showUnavailable, setShowUnavailable] = useState(false);
  const [visibleCount, setVisibleCount] = useState(MODEL_PAGE_SIZE);

  const filteredModels = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return models.filter((model) => {
      if (!showUnavailable && !model.is_available) return false;
      if (!normalizedQuery) return true;
      return model.model_id.toLocaleLowerCase().includes(normalizedQuery);
    });
  }, [models, query, showUnavailable]);

  const visibleModels = filteredModels.slice(0, visibleCount);

  function updateQuery(value: string) {
    setQuery(value);
    setVisibleCount(MODEL_PAGE_SIZE);
  }

  function updateAvailability(value: boolean) {
    setShowUnavailable(value);
    setVisibleCount(MODEL_PAGE_SIZE);
  }

  return (
    <div className={styles.browser}>
      <div className={styles.controls}>
        <input
          aria-label="Filter cached models"
          type="search"
          value={query}
          onChange={(event) => updateQuery(event.target.value)}
          placeholder="Filter model IDs"
        />
        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={showUnavailable}
            onChange={(event) => updateAvailability(event.target.checked)}
          />
          <span>Show unavailable</span>
        </label>
      </div>

      <div aria-atomic="true" aria-live="polite" className={styles.summary}>
        <span>
          Showing {visibleModels.length} of {filteredModels.length} matching models
        </span>
        <span>{models.length} cached</span>
      </div>

      {filteredModels.length === 0 ? (
        <div className={styles.empty} role="status">
          No cached models match these filters.
        </div>
      ) : (
        <div className={styles.list} role="list">
          {visibleModels.map((model) => (
            <div className="model-row" key={model.id} role="listitem">
              <code>{model.model_id}</code>
              <div className="model-badges">
                {model.is_manual && <span className="pill">Manual</span>}
                <span className={`pill ${model.is_available ? "pill-success" : "pill-warning"}`}>
                  {model.is_available ? "Available" : "Missing from latest sync"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {visibleModels.length < filteredModels.length && (
        <div className={styles.actions}>
          <button
            className="button button-secondary"
            type="button"
            onClick={() => setVisibleCount((current) => current + MODEL_PAGE_SIZE)}
          >
            Show {Math.min(MODEL_PAGE_SIZE, filteredModels.length - visibleModels.length)} more
          </button>
        </div>
      )}
    </div>
  );
}

export function ModelSelect({
  label,
  emptyLabel,
  models,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  emptyLabel: string;
  models: CachedModel[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");
  const fieldId = useId();
  const labelId = `${fieldId}-label`;
  const hintId = `${fieldId}-hint`;

  const matchingModels = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    if (!normalizedQuery) return models;
    return models.filter((model) => modelLabel(model).toLocaleLowerCase().includes(normalizedQuery));
  }, [models, query]);

  const selectedModel = models.find((model) => model.id === value);
  const visibleModels = matchingModels.slice(0, MODEL_SELECT_LIMIT);
  const optionModels =
    selectedModel && !visibleModels.some((model) => model.id === selectedModel.id)
      ? [selectedModel, ...visibleModels]
      : visibleModels;

  return (
    <div className={styles.selectField}>
      <span className={styles.fieldLabel} id={labelId}>
        {label}
      </span>
      <div className={styles.selectStack}>
        <input
          aria-label={`Filter options for ${label.toLocaleLowerCase()}`}
          disabled={disabled}
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter by endpoint or model ID"
        />
        <select
          aria-describedby={hintId}
          aria-labelledby={labelId}
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">{emptyLabel}</option>
          {optionModels.map((model) => (
            <option key={model.id} value={model.id}>
              {modelLabel(model)}
              {model.is_available ? "" : " (cached)"}
            </option>
          ))}
        </select>
        <span className={styles.hint} id={hintId}>
          Showing {visibleModels.length} of {matchingModels.length} matching models. Type to narrow the
          list.
        </span>
      </div>
    </div>
  );
}
