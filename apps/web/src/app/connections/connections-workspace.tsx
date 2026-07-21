"use client";

import Link from "next/link";
import { useState } from "react";

import type { IntegrationConnection } from "../../lib/automation-api";
import type { CommunicationAccount } from "../../lib/communication-api";
import { IntegrationPanel } from "../automations/integration-panel";
import { AccountPanel } from "../communications/account-panel";
import { Icon } from "../ui/icons";
import styles from "./connections-workspace.module.css";

type Tab = "discord" | "integrations" | "more";

export function ConnectionsWorkspace({
  initialDiscordAccounts,
  initialIntegrations,
}: {
  initialDiscordAccounts: CommunicationAccount[];
  initialIntegrations: IntegrationConnection[];
}) {
  const [tab, setTab] = useState<Tab>("discord");
  const [discordAccounts, setDiscordAccounts] = useState(initialDiscordAccounts);
  const [integrations, setIntegrations] = useState(initialIntegrations);

  return (
    <div className={styles.workspace}>
      <section aria-label="Connection capabilities" className={styles.overview}>
        <article>
          <header>
            <Icon name="discord" size={16} />
            <h2>Discord</h2>
          </header>
          <p>
            Read only explicitly allowed text channels, search stored messages, prepare AI-assisted
            replies, and send only confirmed responses. Voice, calls, roles, and server
            administration are outside scope.
          </p>
        </article>
        <article>
          <header>
            <Icon name="tools" size={16} />
            <h2>MCP tools</h2>
          </header>
          <p>
            Connect external tool servers and control which capabilities are enabled, available by
            default, or require owner confirmation.
          </p>
        </article>
        <article>
          <header>
            <Icon name="refresh" size={16} />
            <h2>Delivery integrations</h2>
          </header>
          <p>
            Configure SMTP, CalDAV, and outbound webhooks used by email replies, calendar tasks,
            and custom task deliveries.
          </p>
        </article>
      </section>

      <div aria-label="Connection sections" className={styles.tabs} role="tablist">
        <button
          aria-selected={tab === "discord"}
          className={tab === "discord" ? styles.active : ""}
          onClick={() => setTab("discord")}
          role="tab"
          type="button"
        >
          Discord · {discordAccounts.length}
        </button>
        <button
          aria-selected={tab === "integrations"}
          className={tab === "integrations" ? styles.active : ""}
          onClick={() => setTab("integrations")}
          role="tab"
          type="button"
        >
          Integrations · {integrations.length}
        </button>
        <button
          aria-selected={tab === "more"}
          className={tab === "more" ? styles.active : ""}
          onClick={() => setTab("more")}
          role="tab"
          type="button"
        >
          MCP and models
        </button>
      </div>

      {tab === "discord" ? (
        <AccountPanel
          allowedKinds={["discord"]}
          initialAccounts={discordAccounts}
          integrations={integrations}
          onAccountsChange={setDiscordAccounts}
          onInboxChange={async () => undefined}
        />
      ) : tab === "integrations" ? (
        <IntegrationPanel integrations={integrations} onIntegrationsChange={setIntegrations} />
      ) : (
        <section className={styles.links}>
          <Link className={styles.linkCard} href="/settings/tools">
            <header>
              <Icon name="tools" size={16} />
              <h2>Configure MCP tools</h2>
            </header>
            <p>Discover servers, sync tools, and define confirmation boundaries.</p>
          </Link>
          <Link className={styles.linkCard} href="/settings/models">
            <header>
              <Icon name="models" size={16} />
              <h2>Configure model endpoints</h2>
            </header>
            <p>Manage OpenAI-compatible endpoints and model roles used across Aster.</p>
          </Link>
        </section>
      )}
    </div>
  );
}
