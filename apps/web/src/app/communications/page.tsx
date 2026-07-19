import type { Metadata } from "next";

import type { Automation, IntegrationConnection } from "../../lib/automation-api";
import type {
  CommunicationAccount,
  CommunicationRule,
  CommunicationThread,
} from "../../lib/communication-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { CommunicationWorkspace } from "./communication-workspace";

export const metadata: Metadata = { title: "Communications" };

export const dynamic = "force-dynamic";

type InitialCommunicationData = {
  accounts: CommunicationAccount[];
  threads: CommunicationThread[];
  rules: CommunicationRule[];
  automations: Automation[];
  integrations: IntegrationConnection[];
  error: string | null;
};

type WorkspacePageSearchParams = Promise<{ embedded?: string | string[] }>;

async function getInitialData(): Promise<InitialCommunicationData> {
  try {
    const responses = await Promise.all([
      serverApiFetch("/api/communication-accounts"),
      serverApiFetch("/api/communication-threads?limit=100"),
      serverApiFetch("/api/communication-rules"),
      serverApiFetch("/api/automations"),
      serverApiFetch("/api/integrations"),
    ]);
    if (responses.some((response) => !response.ok)) {
      throw new Error("The communication API returned an error.");
    }
    const [accounts, threads, rules, automations, integrations] = await Promise.all(
      responses.map((response) => response.json()),
    );
    return {
      accounts: accounts as CommunicationAccount[],
      threads: threads as CommunicationThread[],
      rules: rules as CommunicationRule[],
      automations: automations as Automation[],
      integrations: integrations as IntegrationConnection[],
      error: null,
    };
  } catch (error) {
    return {
      accounts: [],
      threads: [],
      rules: [],
      automations: [],
      integrations: [],
      error: error instanceof Error ? error.message : "Could not load communications.",
    };
  }
}

export default async function CommunicationsPage({
  searchParams,
}: {
  searchParams: WorkspacePageSearchParams;
}) {
  await requireServerAuth();
  const [initial, params] = await Promise.all([getInitialData(), searchParams]);
  return (
    <AppFrame
      active="communications"
      kicker="Connected channels"
      title="Communications"
      description="Read email and Discord messages, reply manually, and route explicitly allowed events into automations."
      embedded={params.embedded === "1"}
    >
      <CommunicationWorkspace
        initialAccounts={initial.accounts}
        initialThreads={initial.threads}
        initialRules={initial.rules}
        automations={initial.automations}
        integrations={initial.integrations}
        initialError={initial.error}
      />
    </AppFrame>
  );
}
