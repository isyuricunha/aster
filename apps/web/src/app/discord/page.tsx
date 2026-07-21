import type { Metadata } from "next";

import type { CommunicationAccount, CommunicationThread } from "../../lib/communication-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { DiscordWorkspace } from "./discord-workspace";

export const metadata: Metadata = { title: "Discord" };
export const dynamic = "force-dynamic";

type InitialDiscordData = {
  accounts: CommunicationAccount[];
  threads: CommunicationThread[];
  error: string | null;
};

async function getInitialData(): Promise<InitialDiscordData> {
  try {
    const [accountResponse, threadResponse] = await Promise.all([
      serverApiFetch("/api/communication-accounts"),
      serverApiFetch("/api/communication-threads?kind=discord&limit=100"),
    ]);
    if (!accountResponse.ok || !threadResponse.ok) {
      throw new Error("The Discord API returned an error.");
    }
    const accounts = (await accountResponse.json()) as CommunicationAccount[];
    return {
      accounts: accounts.filter((account) => account.kind === "discord"),
      threads: (await threadResponse.json()) as CommunicationThread[],
      error: null,
    };
  } catch (error) {
    return {
      accounts: [],
      threads: [],
      error: error instanceof Error ? error.message : "Could not load Discord.",
    };
  }
}

export default async function DiscordPage() {
  await requireServerAuth();
  const initial = await getInitialData();
  return (
    <AppFrame
      active="discord"
      description="Read synchronized Discord channels and reply from a dedicated chat workspace."
      immersive
      kicker="Connected Discord"
      title="Discord"
    >
      <DiscordWorkspace
        initialAccounts={initial.accounts}
        initialError={initial.error}
        initialThreads={initial.threads}
      />
    </AppFrame>
  );
}
