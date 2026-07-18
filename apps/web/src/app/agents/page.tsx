import type { CachedModel, Persona } from "../../lib/api";
import type {
  Agent,
  AgentCommunicationRule,
  AgentControl,
  AgentNotificationList,
  AgentRun,
} from "../../lib/agent-api";
import type { CommunicationAccount } from "../../lib/communication-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { AgentWorkspace } from "./agent-workspace";

export const dynamic = "force-dynamic";

export type AgentToolOption = {
  id: string;
  server_name: string;
  name: string;
  public_name: string;
  description: string;
  enabled: boolean;
  requires_confirmation: boolean;
  is_available: boolean;
};

export type AgentKnowledgeOption = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  document_count: number;
};

export type InitialAgentData = {
  agents: Agent[];
  runs: AgentRun[];
  rules: AgentCommunicationRule[];
  notifications: AgentNotificationList;
  control: AgentControl;
  models: CachedModel[];
  personas: Persona[];
  tools: AgentToolOption[];
  collections: AgentKnowledgeOption[];
  accounts: CommunicationAccount[];
  error: string | null;
};

async function getInitialData(): Promise<InitialAgentData> {
  try {
    const responses = await Promise.all([
      serverApiFetch("/api/agents"),
      serverApiFetch("/api/agent-runs?limit=100"),
      serverApiFetch("/api/agent-communication-rules"),
      serverApiFetch("/api/agent-notifications?limit=100"),
      serverApiFetch("/api/agent-control"),
      serverApiFetch("/api/models"),
      serverApiFetch("/api/personas"),
      serverApiFetch("/api/mcp-tools"),
      serverApiFetch("/api/knowledge-collections"),
      serverApiFetch("/api/communication-accounts"),
    ]);
    if (responses.some((response) => !response.ok)) {
      throw new Error("The autonomous agent API returned an error.");
    }
    const [
      agents,
      runs,
      rules,
      notifications,
      control,
      models,
      personas,
      tools,
      collections,
      accounts,
    ] = await Promise.all(responses.map((response) => response.json()));
    return {
      agents: agents as Agent[],
      runs: runs as AgentRun[],
      rules: rules as AgentCommunicationRule[],
      notifications: notifications as AgentNotificationList,
      control: control as AgentControl,
      models: models as CachedModel[],
      personas: personas as Persona[],
      tools: tools as AgentToolOption[],
      collections: collections as AgentKnowledgeOption[],
      accounts: accounts as CommunicationAccount[],
      error: null,
    };
  } catch (error) {
    return {
      agents: [],
      runs: [],
      rules: [],
      notifications: { items: [], unread_count: 0, total: 0 },
      control: {
        emergency_stop: false,
        reason: "",
        activated_at: null,
        updated_at: new Date(0).toISOString(),
      },
      models: [],
      personas: [],
      tools: [],
      collections: [],
      accounts: [],
      error: error instanceof Error ? error.message : "Could not load autonomous agents.",
    };
  }
}

export default async function AgentsPage() {
  await requireServerAuth();
  const initial = await getInitialData();
  return (
    <AppFrame
      active="agents"
      kicker="Bounded autonomy"
      title="Agents"
      description="Define persistent goals, explicit permissions, hard budgets, approval boundaries, and fully auditable execution runs."
    >
      <AgentWorkspace initial={initial} />
    </AppFrame>
  );
}
