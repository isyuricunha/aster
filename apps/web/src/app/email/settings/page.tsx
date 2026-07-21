import type { Metadata } from "next";

import type { Automation, IntegrationConnection } from "../../../lib/automation-api";
import type {
  CommunicationAccount,
  CommunicationRule,
} from "../../../lib/communication-api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { EmailSettingsWorkspace } from "./email-settings-workspace";

export const metadata: Metadata = { title: "Email settings" };
export const dynamic = "force-dynamic";

async function getInitialData() {
  const responses = await Promise.all([
    serverApiFetch("/api/communication-accounts"),
    serverApiFetch("/api/communication-rules"),
    serverApiFetch("/api/automations"),
    serverApiFetch("/api/integrations"),
  ]);
  if (responses.some((response) => !response.ok)) {
    throw new Error("The email settings API returned an error.");
  }
  const [allAccounts, allRules, automations, integrations] = await Promise.all(
    responses.map((response) => response.json()),
  );
  const accounts = (allAccounts as CommunicationAccount[]).filter(
    (account) => account.kind === "imap",
  );
  const accountIds = new Set(accounts.map((account) => account.id));
  return {
    accounts,
    rules: (allRules as CommunicationRule[]).filter((rule) => accountIds.has(rule.account_id)),
    automations: automations as Automation[],
    integrations: integrations as IntegrationConnection[],
  };
}

export default async function EmailSettingsPage() {
  await requireServerAuth();
  const initial = await getInitialData();
  return (
    <AppFrame
      active="email"
      description="Configure IMAP accounts, SMTP reply delivery, mailbox discovery, and email-triggered rules."
      kicker="Email configuration"
      title="Email settings"
    >
      <EmailSettingsWorkspace
        automations={initial.automations}
        initialAccounts={initial.accounts}
        initialRules={initial.rules}
        integrations={initial.integrations}
      />
    </AppFrame>
  );
}
