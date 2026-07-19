import type { Metadata } from "next";

import type { ConversationSummary, McpServer, McpTool } from "../../../lib/api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { AdvancedSettings } from "../settings-primitives";
import { SimpleToolSettings } from "./simple-tool-settings";
import { ToolSettings } from "./tool-settings";

export const metadata: Metadata = { title: "Tool settings" };

export const dynamic = "force-dynamic";

type InitialToolSettings = {
  servers: McpServer[];
  tools: McpTool[];
  conversations: ConversationSummary[];
  error: string | null;
};

type SettingsPageSearchParams = Promise<{ embedded?: string | string[] }>;

async function getInitialToolSettings(): Promise<InitialToolSettings> {
  try {
    const [serverResponse, toolResponse, conversationResponse] = await Promise.all([
      serverApiFetch("/api/mcp-servers"),
      serverApiFetch("/api/mcp-tools"),
      serverApiFetch("/api/conversations"),
    ]);
    if (!serverResponse.ok || !toolResponse.ok || !conversationResponse.ok) {
      throw new Error("The tools API returned an error.");
    }
    return {
      servers: (await serverResponse.json()) as McpServer[],
      tools: (await toolResponse.json()) as McpTool[],
      conversations: (await conversationResponse.json()) as ConversationSummary[],
      error: null,
    };
  } catch (error) {
    return {
      servers: [],
      tools: [],
      conversations: [],
      error: error instanceof Error ? error.message : "Could not load tool settings.",
    };
  }
}

export default async function ToolsSettingsPage({
  searchParams,
}: {
  searchParams: SettingsPageSearchParams;
}) {
  await requireServerAuth();
  const [initialData, params] = await Promise.all([getInitialToolSettings(), searchParams]);

  return (
    <AppFrame
      active="tools"
      kicker="Configuration"
      title="Tools"
      description="Connect common MCP servers and control tool permissions without exposing technical transport details by default."
      embedded={params.embedded === "1"}
    >
      <SimpleToolSettings
        initialError={initialData.error}
        initialServers={initialData.servers}
        initialTools={initialData.tools}
      />
      <AdvancedSettings
        description="Stdio transport, encrypted headers and environment values, timeouts, deletion, and per-conversation tool scope."
      >
        <ToolSettings
          initialServers={initialData.servers}
          initialTools={initialData.tools}
          initialConversations={initialData.conversations}
          initialError={initialData.error}
        />
      </AdvancedSettings>
    </AppFrame>
  );
}
