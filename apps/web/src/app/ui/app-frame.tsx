import Link from "next/link";
import type { ReactNode } from "react";

import { AsterMark, Icon, type IconName } from "./icons";

type NavigationKey =
  | "chat"
  | "images"
  | "automations"
  | "models"
  | "persona"
  | "tools"
  | "memory"
  | "account";

type NavigationItem = {
  key: NavigationKey;
  href: string;
  icon: IconName;
  label: string;
};

const workspaceItems: NavigationItem[] = [
  { key: "chat", href: "/", icon: "chat", label: "Chat" },
  { key: "images", href: "/images", icon: "images", label: "Images" },
  {
    key: "automations",
    href: "/automations",
    icon: "refresh",
    label: "Automations",
  },
];

const configurationItems: NavigationItem[] = [
  { key: "models", href: "/settings/models", icon: "models", label: "Models" },
  { key: "persona", href: "/settings/persona", icon: "persona", label: "Personas" },
  { key: "tools", href: "/settings/tools", icon: "tools", label: "Tools" },
  {
    key: "memory",
    href: "/settings/memory",
    icon: "memory",
    label: "Memory & Knowledge",
  },
];

const securityItems: NavigationItem[] = [
  { key: "account", href: "/settings/account", icon: "account", label: "Account" },
];

export function AppFrame({
  active,
  kicker,
  title,
  description,
  children,
}: {
  active: NavigationKey;
  kicker: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="application-shell">
      <aside className="application-sidebar">
        <Link className="workspace-brand" href="/">
          <AsterMark />
          <span>Aster</span>
        </Link>

        <nav className="application-navigation" aria-label="Main navigation">
          <NavigationSection items={workspaceItems} active={active} label="Workspace" />
          <NavigationSection items={configurationItems} active={active} label="Configuration" />
          <NavigationSection items={securityItems} active={active} label="Security" />
        </nav>

        <div className="application-sidebar-footer">
          <div className="workspace-state">
            <span className="workspace-state-dot" />
            <span>Self-hosted</span>
          </div>
          <small>Single-owner workspace</small>
        </div>
      </aside>

      <div className="application-main">
        <header className="application-toolbar">
          <div className="toolbar-path">
            <span>Aster</span>
            <Icon name="chevron-right" size={13} />
            <strong>{title}</strong>
          </div>
          <div className="toolbar-security">
            <Icon name="lock" size={14} />
            <span>Private workspace</span>
          </div>
        </header>

        <main className="settings-content">
          <header className="settings-hero">
            <p>{kicker}</p>
            <h1>{title}</h1>
            <span>{description}</span>
          </header>
          {children}
        </main>
      </div>
    </div>
  );
}

function NavigationSection({
  label,
  items,
  active,
}: {
  label: string;
  items: NavigationItem[];
  active: NavigationKey;
}) {
  return (
    <section className="navigation-section">
      <p>{label}</p>
      <div>
        {items.map((item) => (
          <Link
            aria-current={active === item.key ? "page" : undefined}
            className={`navigation-item ${active === item.key ? "active" : ""}`}
            href={item.href}
            key={item.key}
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
