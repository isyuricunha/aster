"use client";

import { useState } from "react";

import type { Automation, IntegrationConnection } from "../../../lib/automation-api";
import type {
  CommunicationAccount,
  CommunicationRule,
} from "../../../lib/communication-api";
import { AccountPanel } from "../../communications/account-panel";
import { RulePanel } from "../../communications/rule-panel";
import styles from "../../communications/communications.module.css";

type Tab = "accounts" | "rules";

export function EmailSettingsWorkspace({
  initialAccounts,
  initialRules,
  automations,
  integrations,
}: {
  initialAccounts: CommunicationAccount[];
  initialRules: CommunicationRule[];
  automations: Automation[];
  integrations: IntegrationConnection[];
}) {
  const [tab, setTab] = useState<Tab>("accounts");
  const [accounts, setAccounts] = useState(initialAccounts);
  const [rules, setRules] = useState(initialRules);

  return (
    <div className={styles.workspace}>
      <div aria-label="Email settings sections" className={styles.tabs} role="tablist">
        <button
          aria-selected={tab === "accounts"}
          className={tab === "accounts" ? styles.activeTab : ""}
          onClick={() => setTab("accounts")}
          role="tab"
          type="button"
        >
          Accounts <span>{accounts.length}</span>
        </button>
        <button
          aria-selected={tab === "rules"}
          className={tab === "rules" ? styles.activeTab : ""}
          onClick={() => setTab("rules")}
          role="tab"
          type="button"
        >
          Rules <span>{rules.length}</span>
        </button>
      </div>

      {tab === "accounts" ? (
        <AccountPanel
          allowedKinds={["imap"]}
          initialAccounts={accounts}
          integrations={integrations}
          onAccountsChange={setAccounts}
          onInboxChange={async () => undefined}
        />
      ) : (
        <RulePanel
          accounts={accounts}
          automations={automations}
          initialRules={rules}
          onRulesChange={setRules}
        />
      )}
    </div>
  );
}
