import Link from "next/link";

import { AsterMark, Icon, type IconName } from "./icons";

export type NavigationKey =
  | "chat"
  | "communications"
  | "agents"
  | "images"
  | "automations"
  | "models"
  | "persona"
  | "tools"
  | "memory"
  | "account";

export type NavigationSectionKey = "workspace" | "configuration" | "security";

type NavigationItem = {
  key: NavigationKey;
  href: string;
  icon: IconName;
  label: string;
};

type NavigationSection = {
  key: NavigationSectionKey;
  label: string;
  items: readonly NavigationItem[];
};

const NAVIGATION_SECTIONS: readonly NavigationSection[] = [
  {
    key: "workspace",
    label: "Workspace",
    items: [
      { key: "chat", href: "/", icon: "chat", label: "Chat" },
      {
        key: "communications",
        href: "/communications",
        icon: "chat",
        label: "Communications",
      },
      { key: "agents", href: "/agents", icon: "tools", label: "Agents" },
      { key: "images", href: "/images", icon: "images", label: "Images" },
      {
        key: "automations",
        href: "/automations",
        icon: "refresh",
        label: "Automations",
      },
    ],
  },
  {
    key: "configuration",
    label: "Configuration",
    items: [
      { key: "models", href: "/settings/models", icon: "models", label: "Models" },
      { key: "persona", href: "/settings/persona", icon: "persona", label: "Personas" },
      { key: "tools", href: "/settings/tools", icon: "tools", label: "Tools" },
      {
        key: "memory",
        href: "/settings/memory",
        icon: "memory",
        label: "Memory & Knowledge",
      },
    ],
  },
  {
    key: "security",
    label: "Security",
    items: [{ key: "account", href: "/settings/account", icon: "account", label: "Account" }],
  },
];

export function WorkspaceBrand() {
  return (
    <Link className="workspace-brand" href="/">
      <AsterMark />
      <span>Aster</span>
    </Link>
  );
}

export function WorkspaceNavigation({
  active,
  className = "application-navigation",
  sections = ["workspace", "configuration", "security"],
  label = "Main navigation",
}: {
  active: NavigationKey;
  className?: string;
  sections?: readonly NavigationSectionKey[];
  label?: string;
}) {
  const visibleSections = NAVIGATION_SECTIONS.filter((section) => sections.includes(section.key));

  return (
    <nav className={className} aria-label={label}>
      {visibleSections.map((section) => (
        <section className="navigation-section" key={section.key}>
          <p>{section.label}</p>
          <div>
            {section.items.map((item) => (
              <Link
                aria-current={active === item.key ? "page" : undefined}
                aria-label={item.label}
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
      ))}
    </nav>
  );
}

export function MobileWorkspaceNavigation({
  active,
  title,
}: {
  active: NavigationKey;
  title: string;
}) {
  return (
    <details className="mobile-workspace-navigation">
      <summary aria-label="Workspace navigation">
        <Icon name="menu" size={18} />
        <span>{title}</span>
      </summary>
      <div className="mobile-navigation-panel">
        <div className="mobile-navigation-header">
          <WorkspaceBrand />
          <span>Private workspace</span>
        </div>
        <WorkspaceNavigation active={active} className="mobile-navigation-sections" />
        <div className="mobile-navigation-footer">
          <span className="workspace-state-dot" />
          <span>Self-hosted</span>
        </div>
      </div>
    </details>
  );
}
