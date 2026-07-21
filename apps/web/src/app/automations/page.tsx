import type { Metadata } from "next";

import type { CachedModel, Persona } from "../../lib/api";
import type {
  Automation,
  AutomationRun,
  IntegrationConnection,
} from "../../lib/automation-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { AutomationWorkspace } from "./automation-workspace";

export const metadata: Metadata = { title: "Tasks" };
export const dynamic = "force-dynamic";

type InitialAutomationData = {
  automations: Automation[];
  runs: AutomationRun[];
  integrations: IntegrationConnection[];
  models: CachedModel[];
  personas: Persona[];
  error: string | null;
};

type AutomationsPageSearchParams = Promise<{ embedded?: string | string[] }>;

async function getInitialData(): Promise<InitialAutomationData> {
  try {
    const responses = await Promise.all([
      serverApiFetch("/api/tasks"),
      serverApiFetch("/api/automation-runs?limit=100"),
      serverApiFetch("/api/integrations"),
      serverApiFetch("/api/models"),
      serverApiFetch("/api/personas"),
    ]);
    if (responses.some((response) => !response.ok)) {
      throw new Error("The Tasks API returned an error.");
    }
    const [automations, runs, integrations, models, personas] = await Promise.all(
      responses.map((response) => response.json()),
    );
    return {
      automations: automations as Automation[],
      runs: runs as AutomationRun[],
      integrations: integrations as IntegrationConnection[],
      models: models as CachedModel[],
      personas: personas as Persona[],
      error: null,
    };
  } catch (error) {
    return {
      automations: [],
      runs: [],
      integrations: [],
      models: [],
      personas: [],
      error: error instanceof Error ? error.message : "Could not load tasks.",
    };
  }
}

export default async function AutomationsPage({
  searchParams,
}: {
  searchParams: AutomationsPageSearchParams;
}) {
  await requireServerAuth();
  const [initial, params] = await Promise.all([getInitialData(), searchParams]);
  return (
    <AppFrame
      active="automations"
      description="Run built-in maintenance tasks, schedule custom work, and inspect every attempt."
      embedded={params.embedded === "1"}
      kicker="Background work"
      title="Tasks"
    >
      {initial.error ? (
        <div className="banner banner-error" role="alert">
          {initial.error}
        </div>
      ) : null}
      <AutomationWorkspace
        initialAutomationId={null}
        initialAutomations={initial.automations}
        initialIntegrations={initial.integrations}
        initialRuns={initial.runs}
        models={initial.models}
        personas={initial.personas}
      />
    </AppFrame>
  );
}
