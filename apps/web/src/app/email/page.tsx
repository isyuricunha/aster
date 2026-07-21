import type { Metadata } from "next";

import type { CommunicationAccount, CommunicationThread } from "../../lib/communication-api";
import { requireServerAuth, serverApiFetch } from "../../lib/server-api";
import { AppFrame } from "../ui/app-frame";
import { EmailWorkspace } from "./email-workspace";

export const metadata: Metadata = { title: "Email" };
export const dynamic = "force-dynamic";

const EMAIL_THREAD_PAGE_SIZE = 100;

type InitialEmailData = {
  accounts: CommunicationAccount[];
  threads: CommunicationThread[];
  error: string | null;
};

async function getAllEmailThreads(): Promise<CommunicationThread[]> {
  const threads: CommunicationThread[] = [];
  let offset = 0;

  while (true) {
    const response = await serverApiFetch(
      `/api/communication-threads?kind=email&offset=${offset}&limit=${EMAIL_THREAD_PAGE_SIZE}`,
    );
    if (!response.ok) throw new Error("The email API returned an error.");
    const page = (await response.json()) as CommunicationThread[];
    threads.push(...page);
    if (page.length < EMAIL_THREAD_PAGE_SIZE) return threads;
    offset += page.length;
  }
}

async function getInitialData(): Promise<InitialEmailData> {
  try {
    const [accountResponse, threads] = await Promise.all([
      serverApiFetch("/api/communication-accounts"),
      getAllEmailThreads(),
    ]);
    if (!accountResponse.ok) {
      throw new Error("The email API returned an error.");
    }
    const accounts = (await accountResponse.json()) as CommunicationAccount[];
    return {
      accounts: accounts.filter((account) => account.kind === "imap"),
      threads,
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
