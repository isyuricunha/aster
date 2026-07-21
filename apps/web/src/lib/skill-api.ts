import { apiRequest } from "./api";

export type SkillStatus = "draft" | "published" | "archived";
export type SkillSourceType = "manual" | "imported" | "generated";
export type SkillAuditStatus =
  | "pending"
  | "auditing"
  | "passed"
  | "needs_review"
  | "duplicate"
  | "trivial"
  | "failed";

export type SkillTestCase = {
  input: string;
  expected: string;
};

export type Skill = {
  id: string;
  name: string;
  description: string;
  instructions: string;
  status: SkillStatus;
  source_type: SkillSourceType;
  tags: string[];
  trigger_phrases: string[];
  test_cases: SkillTestCase[];
  audit_status: SkillAuditStatus;
  audit_score: number | null;
  audit_report: Record<string, unknown>;
  duplicate_of_id: string | null;
  duplicate_name: string | null;
  content_revision: number;
  audited_revision: number | null;
  audited_at: string | null;
  published_at: string | null;
  last_error: string | null;
  attempt_count: number;
  created_at: string;
  updated_at: string;
};

export type SkillWrite = {
  name: string;
  description: string;
  instructions: string;
  source_type: SkillSourceType;
  tags: string[];
  trigger_phrases: string[];
  test_cases: SkillTestCase[];
};

export type SkillAuditAttempt = {
  id: string;
  skill_id: string;
  automation_run_id: string | null;
  attempt_number: number;
  stage: "audit" | "self_edit" | "teacher_rewrite" | "recheck";
  provider_model_id: string | null;
  verdict: "pass" | "revise" | "duplicate" | "trivial" | "failed";
  score: number | null;
  passed_tests: number;
  total_tests: number;
  details: Record<string, unknown>;
  created_at: string;
};

export type SkillAuditPreferences = {
  auto_approve_threshold: number;
  max_self_edit_attempts: number;
  max_skills_per_run: number;
  teacher_rewrite_enabled: boolean;
  teacher_model_id: string | null;
  teacher_model_name: string | null;
  created_at: string;
  updated_at: string;
};

export type SkillAuditQueue = {
  skill_id: string;
  task_id: string;
  run_id: string;
  status: "queued";
};

export function listSkills(): Promise<Skill[]> {
  return apiRequest<Skill[]>("/api/skills");
}

export function createSkill(payload: SkillWrite): Promise<Skill> {
  return apiRequest<Skill>("/api/skills", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSkill(id: string, payload: SkillWrite): Promise<Skill> {
  return apiRequest<Skill>(`/api/skills/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteSkill(id: string): Promise<void> {
  return apiRequest<void>(`/api/skills/${id}`, { method: "DELETE" });
}

export function setSkillStatus(id: string, status: SkillStatus): Promise<Skill> {
  return apiRequest<Skill>(`/api/skills/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export function queueSkillAudit(id: string): Promise<SkillAuditQueue> {
  return apiRequest<SkillAuditQueue>(`/api/skills/${id}/audit`, { method: "POST" });
}

export function listSkillAuditAttempts(skillId?: string): Promise<SkillAuditAttempt[]> {
  const query = skillId ? `?skill_id=${encodeURIComponent(skillId)}` : "";
  return apiRequest<SkillAuditAttempt[]>(`/api/skill-audit-attempts${query}`);
}

export function getSkillAuditPreferences(): Promise<SkillAuditPreferences> {
  return apiRequest<SkillAuditPreferences>("/api/skill-audit-preferences");
}

export function updateSkillAuditPreferences(
  payload: Omit<SkillAuditPreferences, "teacher_model_name" | "created_at" | "updated_at">,
): Promise<SkillAuditPreferences> {
  return apiRequest<SkillAuditPreferences>("/api/skill-audit-preferences", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
