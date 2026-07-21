import type { Metadata } from "next";

import type { CachedModel } from "../../lib/api";
import type {
  Skill,
  SkillAuditAttempt,
  SkillAuditPreferences,
} from "../../lib/skill-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { SkillsWorkspace } from "./skills-workspace";

export const metadata: Metadata = { title: "Skills" };
export const dynamic = "force-dynamic";

type SkillsPageSearchParams = Promise<{ embedded?: string | string[] }>;

type InitialSkillsData = {
  skills: Skill[];
  attempts: SkillAuditAttempt[];
  preferences: SkillAuditPreferences;
  models: CachedModel[];
  error: string | null;
};

const EMPTY_PREFERENCES: SkillAuditPreferences = {
  auto_approve_threshold: 85,
  max_self_edit_attempts: 2,
  max_skills_per_run: 10,
  teacher_rewrite_enabled: false,
  teacher_model_id: null,
  teacher_model_name: null,
  created_at: "",
  updated_at: "",
};

async function getInitialData(): Promise<InitialSkillsData> {
  try {
    const responses = await Promise.all([
      serverApiFetch("/api/skills"),
      serverApiFetch("/api/skill-audit-attempts?limit=250"),
      serverApiFetch("/api/skill-audit-preferences"),
      serverApiFetch("/api/models"),
    ]);
    if (responses.some((response) => !response.ok)) {
      throw new Error("The Skills API returned an error.");
    }
    const [skills, attempts, preferences, models] = await Promise.all(
      responses.map((response) => response.json()),
    );
    return {
      skills: skills as Skill[],
      attempts: attempts as SkillAuditAttempt[],
      preferences: preferences as SkillAuditPreferences,
      models: models as CachedModel[],
      error: null,
    };
  } catch (error) {
    return {
      skills: [],
      attempts: [],
      preferences: EMPTY_PREFERENCES,
      models: [],
      error: error instanceof Error ? error.message : "Could not load skills.",
    };
  }
}

export default async function SkillsPage({
  searchParams,
}: {
  searchParams: SkillsPageSearchParams;
}) {
  await requireServerAuth();
  const [initial, params] = await Promise.all([getInitialData(), searchParams]);
  return (
    <AppFrame
      active="skills"
      kicker="Reusable capabilities"
      title="Skills"
      description="Create reusable instruction bundles and let Skills Audit test, refine, and publish them."
      embedded={params.embedded === "1"}
    >
      {initial.error ? (
        <div className="banner banner-error" role="alert">
          {initial.error}
        </div>
      ) : null}
      <SkillsWorkspace
        initialAttempts={initial.attempts}
        initialPreferences={initial.preferences}
        initialSkills={initial.skills}
        models={initial.models}
      />
    </AppFrame>
  );
}
