import type { Metadata } from "next";

import type { IntegrationConnection } from "../../lib/automation-api";
import type { CommunicationAccount } from "../../lib/communication-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { ConnectionsWorkspace } from "./connections-workspace";

export const metadata: Metadata = { title: "Connections" };
export const dynamic = "force-dynamic";

async function getInitialData() {
  const [accountResponse, integrationResponse] = await Promise.all([
    serverApiFetch("/api/communication-accounts"),
    serverApiFetch("/api/integrations"),
  ]);
  if (!accountResponse.ok || !integrationResponse.ok) {
    throw new Error("The connections API returned an error.");
  }
  const accounts = (await accountResponse.json()) as CommunicationAccount[];
  return {
    discordAccounts: accounts.filter((account) => account.kind === "discord"),
    integrations: (await integrationResponse.json()) as IntegrationConnection[],
  };
}

export default async function ConnectionsPage() {
  await requireServerAuth();
  const initial = await getInitialData();
  return (
    <AppFrame
      active="connections"
      description="Connect Discord, MCP servers, calendars, SMTP delivery, and other bounded external capabilities."
      kicker="Tools"
      title="Connections"
    >
      <ConnectionsWorkspace
        initialDiscordAccounts={initial.discordAccounts}
        initialIntegrations={initial.integrations}
      />
    </AppFrame>
  );
}
