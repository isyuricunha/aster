import type { Metadata } from "next";

import type { CommunicationAccount, CommunicationThread } from "../../lib/communication-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { EmailWorkspace } from "./email-workspace";

export const metadata: Metadata = { title: "Email" };
export const dynamic = "force-dynamic";

type InitialEmailData = {
  accounts: CommunicationAccount[];
  threads: CommunicationThread[];
  error: string | null;
};

async function getInitialData(): Promise<InitialEmailData> {
  try {
    const [accountResponse, threadResponse] = await Promise.all([
      serverApiFetch("/api/communication-accounts"),
      serverApiFetch("/api/communication-threads?kind=email&limit=100"),
    ]);
    if (!accountResponse.ok || !threadResponse.ok) {
      throw new Error("The email API returned an error.");
    }
    const accounts = (await accountResponse.json()) as CommunicationAccount[];
    return {
      accounts: accounts.filter((account) => account.kind === "imap"),
      threads: (await threadResponse.json()) as CommunicationThread[],
      error: null,
    };
  } catch (error) {
    return {
      accounts: [],
      threads: [],
      error: error instanceof Error ? error.message : "Could not load email.",
    };
  }
}

export default async function EmailPage() {
  await requireServerAuth();
  const initial = await getInitialData();
  return (
    <AppFrame
      active="email"
      description="Read and reply to synchronized email in a full-size workspace."
      immersive
      kicker="Private mail"
      title="Email"
    >
      <EmailWorkspace
        initialAccounts={initial.accounts}
        initialError={initial.error}
        initialThreads={initial.threads}
      />
    </AppFrame>
  );
}
