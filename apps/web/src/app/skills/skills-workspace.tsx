"use client";

import { useMemo, useState, type FormEvent } from "react";

import type { CachedModel } from "../../lib/api";
import {
  createSkill,
  deleteSkill,
  getSkillAuditPreferences,
  listSkillAuditAttempts,
  listSkills,
  queueSkillAudit,
  setSkillStatus,
  updateSkill,
  updateSkillAuditPreferences,
  type Skill,
  type SkillAuditAttempt,
  type SkillAuditPreferences,
  type SkillSourceType,
  type SkillStatus,
  type SkillTestCase,
  type SkillWrite,
} from "../../lib/skill-api";
import { Icon } from "../ui/icons";
import styles from "./skills.module.css";

type WorkspaceTab = "library" | "audit";

type SkillDraft = {
  name: string;
  description: string;
  instructions: string;
  sourceType: SkillSourceType;
  tags: string;
  triggerPhrases: string;
  testCases: SkillTestCase[];
};

type PreferenceDraft = {
  threshold: string;
  selfEdits: string;
  batchSize: string;
  teacherEnabled: boolean;
  teacherModelId: string;
};

const EMPTY_DRAFT: SkillDraft = {
  name: "",
  description: "",
  instructions: "",
  sourceType: "manual",
  tags: "",
  triggerPhrases: "",
  testCases: [],
};

function draftFromSkill(skill: Skill): SkillDraft {
  return {
    name: skill.name,
    description: skill.description,
    instructions: skill.instructions,
    sourceType: skill.source_type,
    tags: skill.tags.join(", "),
    triggerPhrases: skill.trigger_phrases.join("\n"),
    testCases: skill.test_cases,
  };
}

function preferenceDraft(preferences: SkillAuditPreferences): PreferenceDraft {
  return {
    threshold: String(preferences.auto_approve_threshold),
    selfEdits: String(preferences.max_self_edit_attempts),
    batchSize: String(preferences.max_skills_per_run),
    teacherEnabled: preferences.teacher_rewrite_enabled,
    teacherModelId: preferences.teacher_model_id ?? "",
  };
}

function splitMetadata(value: string, separator: RegExp): string[] {
  return Array.from(
    new Map(
      value
        .split(separator)
        .map((item) => item.trim())
        .filter(Boolean)
        .map((item): [string, string] => [item.toLocaleLowerCase(), item]),
    ).values(),
  );
}

function payloadFromDraft(draft: SkillDraft): SkillWrite {
  return {
    name: draft.name.trim(),
    description: draft.description.trim(),
    instructions: draft.instructions.trim(),
    source_type: draft.sourceType,
    tags: splitMetadata(draft.tags, /[,\n]/),
    trigger_phrases: splitMetadata(draft.triggerPhrases, /\n/),
    test_cases: draft.testCases.filter((test) => test.input.trim() && test.expected.trim()),
  };
}

function formatDate(value: string | null): string {
  if (!value) return "Not yet";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function scoreLabel(skill: Skill): string {
  return skill.audit_score === null ? "—" : `${skill.audit_score}/100`;
}

export function SkillsWorkspace({
  initialSkills,
  initialAttempts,
  initialPreferences,
  models,
}: {
  initialSkills: Skill[];
  initialAttempts: SkillAuditAttempt[];
  initialPreferences: SkillAuditPreferences;
  models: CachedModel[];
}) {
  const [tab, setTab] = useState<WorkspaceTab>("library");
  const [skills, setSkills] = useState(initialSkills);
  const [attempts, setAttempts] = useState(initialAttempts);
  const [preferences, setPreferences] = useState(initialPreferences);
  const [preferenceForm, setPreferenceForm] = useState(() => preferenceDraft(initialPreferences));
  const [selectedId, setSelectedId] = useState<string | null>(initialSkills[0]?.id ?? null);
  const [creating, setCreating] = useState(initialSkills.length === 0);
  const [draft, setDraft] = useState<SkillDraft>(
    initialSkills[0] ? draftFromSkill(initialSkills[0]) : EMPTY_DRAFT,
  );
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selected = skills.find((skill) => skill.id === selectedId) ?? null;
  const selectedAttempts = attempts
    .filter((attempt) => attempt.skill_id === selectedId)
    .sort((left, right) => right.attempt_number - left.attempt_number);
  const availableModels = models.filter((model) => model.is_available);
  const filteredSkills = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    if (!normalized) return skills;
    return skills.filter((skill) =>
      [skill.name, skill.description, skill.tags.join(" "), skill.audit_status, skill.status]
        .join(" ")
        .toLocaleLowerCase()
        .includes(normalized),
    );
  }, [query, skills]);

  function choose(skill: Skill) {
    setSelectedId(skill.id);
    setDraft(draftFromSkill(skill));
    setCreating(false);
    setNotice(null);
    setError(null);
  }

  function beginCreate() {
    setSelectedId(null);
    setDraft(EMPTY_DRAFT);
    setCreating(true);
    setNotice(null);
    setError(null);
  }

  async function refresh(selectId = selectedId) {
    const [nextSkills, nextAttempts, nextPreferences] = await Promise.all([
      listSkills(),
      listSkillAuditAttempts(),
      getSkillAuditPreferences(),
    ]);
    setSkills(nextSkills);
    setAttempts(nextAttempts);
    setPreferences(nextPreferences);
    setPreferenceForm(preferenceDraft(nextPreferences));
    const nextSelected = nextSkills.find((skill) => skill.id === selectId) ?? nextSkills[0] ?? null;
    if (nextSelected) choose(nextSelected);
    else beginCreate();
  }

  async function saveSkill(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = payloadFromDraft(draft);
    if (!payload.name || !payload.instructions) {
      setError("Name and instructions are required.");
      return;
    }
    setBusy("save");
    setNotice(null);
    setError(null);
    try {
      const saved = creating
        ? await createSkill(payload)
        : await updateSkill(selectedId as string, payload);
      await refresh(saved.id);
      setNotice(creating ? "Skill created and queued for audit." : "Skill updated and re-queued for audit.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The skill could not be saved.");
    } finally {
      setBusy(null);
    }
  }

  async function auditSelected() {
    if (!selected) return;
    setBusy("audit");
    setNotice(null);
    setError(null);
    try {
      await queueSkillAudit(selected.id);
      await refresh(selected.id);
      setNotice("Skills Audit queued for this skill.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The audit could not be queued.");
    } finally {
      setBusy(null);
    }
  }

  async function changeStatus(status: SkillStatus) {
    if (!selected) return;
    setBusy("status");
    setNotice(null);
    setError(null);
    try {
      const updated = await setSkillStatus(selected.id, status);
      await refresh(updated.id);
      setNotice(`Skill moved to ${status}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The skill status could not be changed.");
    } finally {
      setBusy(null);
    }
  }

  async function removeSelected() {
    if (!selected || !window.confirm(`Delete ${selected.name} and its audit history?`)) return;
    setBusy("delete");
    setNotice(null);
    setError(null);
    try {
      await deleteSkill(selected.id);
      await refresh(null);
      setNotice("Skill deleted.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The skill could not be deleted.");
    } finally {
      setBusy(null);
    }
  }

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy("preferences");
    setNotice(null);
    setError(null);
    try {
      const updated = await updateSkillAuditPreferences({
        auto_approve_threshold: Number(preferenceForm.threshold),
        max_self_edit_attempts: Number(preferenceForm.selfEdits),
        max_skills_per_run: Number(preferenceForm.batchSize),
        teacher_rewrite_enabled: preferenceForm.teacherEnabled,
        teacher_model_id: preferenceForm.teacherEnabled
          ? preferenceForm.teacherModelId || null
          : null,
      });
      setPreferences(updated);
      setPreferenceForm(preferenceDraft(updated));
      setNotice("Skills Audit settings saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Audit settings could not be saved.");
    } finally {
      setBusy(null);
    }
  }

  function addTestCase() {
    setDraft({ ...draft, testCases: [...draft.testCases, { input: "", expected: "" }] });
  }

  function updateTestCase(index: number, values: Partial<SkillTestCase>) {
    setDraft({
      ...draft,
      testCases: draft.testCases.map((test, testIndex) =>
        testIndex === index ? { ...test, ...values } : test,
      ),
    });
  }

  return (
    <div className={styles.workspace}>
      <div className={styles.tabs} role="tablist" aria-label="Skill sections">
        <button
          aria-selected={tab === "library"}
          className={tab === "library" ? styles.activeTab : ""}
          onClick={() => setTab("library")}
          role="tab"
          type="button"
        >
          Skill library <span>{skills.length}</span>
        </button>
        <button
          aria-selected={tab === "audit"}
          className={tab === "audit" ? styles.activeTab : ""}
          onClick={() => setTab("audit")}
          role="tab"
          type="button"
        >
          Audit settings
        </button>
        <button className={styles.refreshButton} onClick={() => void refresh()} type="button">
          <Icon name="refresh" size={14} /> Refresh
        </button>
      </div>

      {notice ? <div className={styles.notice}>{notice}</div> : null}
      {error ? <div className={styles.error}>{error}</div> : null}

      {tab === "library" ? (
        <div className={styles.library}>
          <aside className={styles.skillList} aria-label="Skills">
            <div className={styles.listActions}>
              <button className={styles.primaryButton} onClick={beginCreate} type="button">
                <Icon name="new-chat" size={14} /> New skill
              </button>
              <label>
                <Icon name="search" size={14} />
                <input
                  aria-label="Search skills"
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search skills"
                  value={query}
                />
              </label>
            </div>
            <div className={styles.skillItems}>
              {filteredSkills.map((skill) => (
                <button
                  aria-pressed={!creating && selectedId === skill.id}
                  className={!creating && selectedId === skill.id ? styles.selectedSkill : ""}
                  key={skill.id}
                  onClick={() => choose(skill)}
                  type="button"
                >
                  <span className={`${styles.statusDot} ${styles[`audit_${skill.audit_status}`]}`} />
                  <div>
                    <strong>{skill.name}</strong>
                    <small>{skill.description || "No description"}</small>
                    <span>
                      {skill.status} · {statusLabel(skill.audit_status)} · {scoreLabel(skill)}
                    </span>
                  </div>
                </button>
              ))}
              {!filteredSkills.length ? (
                <div className={styles.emptyList}>No matching skills.</div>
              ) : null}
            </div>
          </aside>

          <form className={styles.editor} onSubmit={(event) => void saveSkill(event)}>
            <header className={styles.editorHeader}>
              <div>
                <p>{creating ? "New reusable capability" : "Skill detail"}</p>
                <h2>{draft.name || "Untitled skill"}</h2>
                <span>
                  {selected
                    ? `Revision ${selected.content_revision} · ${statusLabel(selected.audit_status)}`
                    : "Draft a precise instruction bundle, triggers, and behavioral tests."}
                </span>
              </div>
              <div className={styles.headerActions}>
                {!creating && selected ? (
                  <>
                    <button disabled={Boolean(busy)} onClick={() => void auditSelected()} type="button">
                      {busy === "audit" ? "Queueing…" : "Run audit"}
                    </button>
                    <select
                      aria-label="Skill status"
                      disabled={Boolean(busy)}
                      onChange={(event) => void changeStatus(event.target.value as SkillStatus)}
                      value={selected.status}
                    >
                      <option value="draft">Draft</option>
                      <option value="published">Published</option>
                      <option value="archived">Archived</option>
                    </select>
                    <button disabled={Boolean(busy)} onClick={() => void removeSelected()} type="button">
                      Delete
                    </button>
                  </>
                ) : null}
                <button className={styles.primaryButton} disabled={Boolean(busy)} type="submit">
                  {busy === "save" ? "Saving…" : "Save skill"}
                </button>
              </div>
            </header>

            {selected ? <SkillAuditSummary skill={selected} /> : null}

            <section className={styles.formSection}>
              <div className={styles.gridTwo}>
                <label>
                  Name
                  <input
                    maxLength={160}
                    onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                    required
                    value={draft.name}
                  />
                </label>
                <label>
                  Source
                  <select
                    onChange={(event) =>
                      setDraft({ ...draft, sourceType: event.target.value as SkillSourceType })
                    }
                    value={draft.sourceType}
                  >
                    <option value="manual">Manual</option>
                    <option value="imported">Imported</option>
                    <option value="generated">Generated</option>
                  </select>
                </label>
                <label className={styles.spanTwo}>
                  Description
                  <input
                    maxLength={500}
                    onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                    value={draft.description}
                  />
                </label>
                <label className={styles.spanTwo}>
                  Instructions
                  <textarea
                    onChange={(event) => setDraft({ ...draft, instructions: event.target.value })}
                    required
                    rows={14}
                    value={draft.instructions}
                  />
                </label>
                <label>
                  Tags
                  <textarea
                    onChange={(event) => setDraft({ ...draft, tags: event.target.value })}
                    placeholder="translation, localization, terminology"
                    rows={4}
                    value={draft.tags}
                  />
                  <small>Comma or line separated. Audit narrows this to eight.</small>
                </label>
                <label>
                  Trigger phrases
                  <textarea
                    onChange={(event) =>
                      setDraft({ ...draft, triggerPhrases: event.target.value })
                    }
                    placeholder={"translate this game file\nreview localization terms"}
                    rows={4}
                    value={draft.triggerPhrases}
                  />
                  <small>One specific phrase per line. Audit narrows this to twelve.</small>
                </label>
              </div>
            </section>

            <section className={styles.formSection}>
              <div className={styles.sectionHeading}>
                <div>
                  <p>Behavioral tests</p>
                  <h3>What must this skill do?</h3>
                </div>
                <button onClick={addTestCase} type="button">Add test</button>
              </div>
              <div className={styles.testCases}>
                {draft.testCases.map((test, index) => (
                  <article key={index}>
                    <label>
                      Input
                      <textarea
                        onChange={(event) => updateTestCase(index, { input: event.target.value })}
                        rows={3}
                        value={test.input}
                      />
                    </label>
                    <label>
                      Expected behavior
                      <textarea
                        onChange={(event) => updateTestCase(index, { expected: event.target.value })}
                        rows={3}
                        value={test.expected}
                      />
                    </label>
                    <button
                      aria-label={`Remove test ${index + 1}`}
                      onClick={() =>
                        setDraft({
                          ...draft,
                          testCases: draft.testCases.filter((_, testIndex) => testIndex !== index),
                        })
                      }
                      type="button"
                    >
                      Remove
                    </button>
                  </article>
                ))}
                {!draft.testCases.length ? (
                  <div className={styles.emptyTests}>
                    Skills Audit can generate tests, but adding examples here gives it a sharper contract.
                  </div>
                ) : null}
              </div>
            </section>

            {!creating && selected ? (
              <section className={styles.attemptSection}>
                <div className={styles.sectionHeading}>
                  <div>
                    <p>Audit history</p>
                    <h3>{selectedAttempts.length} attempt(s)</h3>
                  </div>
                </div>
                <div className={styles.attempts}>
                  {selectedAttempts.map((attempt) => (
                    <article key={attempt.id}>
                      <span className={`${styles.statusDot} ${styles[`verdict_${attempt.verdict}`]}`} />
                      <div>
                        <strong>
                          {attempt.stage.replaceAll("_", " ")} · {attempt.verdict}
                        </strong>
                        <span>
                          Score {attempt.score ?? "—"} · {attempt.passed_tests}/{attempt.total_tests}
                          {" "}tests · {attempt.provider_model_id ?? "deterministic"}
                        </span>
                        <small>{formatDate(attempt.created_at)}</small>
                      </div>
                    </article>
                  ))}
                  {!selectedAttempts.length ? (
                    <div className={styles.emptyTests}>No audit attempts yet.</div>
                  ) : null}
                </div>
              </section>
            ) : null}
          </form>
        </div>
      ) : (
        <form className={styles.auditSettings} onSubmit={(event) => void savePreferences(event)}>
          <header>
            <p>Skills Audit policy</p>
            <h2>Bounded review and auto-approval</h2>
            <span>
              Audit uses the Utility model, keeps failed or uncertain skills as drafts, and only
              publishes skills that pass every configured gate.
            </span>
          </header>
          <div className={styles.preferenceGrid}>
            <label>
              Auto-approve score
              <input
                max={100}
                min={0}
                onChange={(event) =>
                  setPreferenceForm({ ...preferenceForm, threshold: event.target.value })
                }
                type="number"
                value={preferenceForm.threshold}
              />
              <small>Current threshold: {preferences.auto_approve_threshold}/100.</small>
            </label>
            <label>
              Self-edit retries
              <input
                max={5}
                min={0}
                onChange={(event) =>
                  setPreferenceForm({ ...preferenceForm, selfEdits: event.target.value })
                }
                type="number"
                value={preferenceForm.selfEdits}
              />
              <small>Each retry must narrow or materially improve the skill.</small>
            </label>
            <label>
              Skills per task run
              <input
                max={25}
                min={1}
                onChange={(event) =>
                  setPreferenceForm({ ...preferenceForm, batchSize: event.target.value })
                }
                type="number"
                value={preferenceForm.batchSize}
              />
              <small>The built-in task becomes due after five new pending skills.</small>
            </label>
            <label className={styles.checkLabel}>
              <input
                checked={preferenceForm.teacherEnabled}
                onChange={(event) =>
                  setPreferenceForm({
                    ...preferenceForm,
                    teacherEnabled: event.target.checked,
                  })
                }
                type="checkbox"
              />
              <span>
                <strong>Enable teacher rewrite</strong>
                <small>Use an explicit second model after normal self-edit retries fail.</small>
              </span>
            </label>
            <label className={styles.spanTwo}>
              Teacher model
              <select
                disabled={!preferenceForm.teacherEnabled}
                onChange={(event) =>
                  setPreferenceForm({ ...preferenceForm, teacherModelId: event.target.value })
                }
                value={preferenceForm.teacherModelId}
              >
                <option value="">Select a model</option>
                {availableModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.endpoint_name} / {model.model_id}
                  </option>
                ))}
              </select>
              <small>
                The normal auditor still uses Utility. Teacher rewrite is optional and never silently
                falls back to an unspecified model.
              </small>
            </label>
          </div>
          <div className={styles.settingsActions}>
            <button className={styles.primaryButton} disabled={Boolean(busy)} type="submit">
              {busy === "preferences" ? "Saving…" : "Save audit settings"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function SkillAuditSummary({ skill }: { skill: Skill }) {
  const report = skill.audit_report;
  const passedTests = typeof report.passed_tests === "number" ? report.passed_tests : null;
  const totalTests = typeof report.total_tests === "number" ? report.total_tests : null;
  const rationale = typeof report.rationale === "string" ? report.rationale : null;

  return (
    <section className={styles.auditSummary}>
      <article>
        <span>Audit</span>
        <strong>{statusLabel(skill.audit_status)}</strong>
        <small>{skill.audited_revision ? `Revision ${skill.audited_revision}` : "Pending"}</small>
      </article>
      <article>
        <span>Score</span>
        <strong>{scoreLabel(skill)}</strong>
        <small>{skill.attempt_count} attempt(s)</small>
      </article>
      <article>
        <span>Tests</span>
        <strong>{passedTests === null ? "—" : `${passedTests}/${totalTests}`}</strong>
        <small>Behavioral evaluation</small>
      </article>
      <article>
        <span>Last audit</span>
        <strong>{formatDate(skill.audited_at)}</strong>
        <small>{skill.duplicate_name ? `Duplicates ${skill.duplicate_name}` : rationale ?? "No report"}</small>
      </article>
      {skill.last_error ? <div className={styles.auditError}>{skill.last_error}</div> : null}
    </section>
  );
}
