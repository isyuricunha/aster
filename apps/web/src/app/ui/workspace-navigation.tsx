"use client";

import Link from "next/link";
import type { MouseEvent } from "react";

import { OPEN_COMMAND_PALETTE_EVENT } from "./command-palette-host";
import { AsterMark, Icon, type IconName } from "./icons";
import {
  OPEN_SETTINGS_EVENT,
  OPEN_WORKSPACE_WINDOW_EVENT,
  type SettingsSection,
  type WorkspaceWindowKey,
} from "./workspace-window-host";

export type NavigationKey =
  | "chat"
  | "email"
  | "discord"
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
  settingsSection?: SettingsSection;
  workspaceWindow?: WorkspaceWindowKey;
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
      { key: "email", href: "/email", icon: "email", label: "Email" },
      { key: "discord", href: "/discord", icon: "discord", label: "Discord" },
      {
        key: "agents",
        href: "/agents",
        icon: "tools",
        label: "Agents",
        workspaceWindow: "agents",
      },
      {
        key: "images",
        href: "/images",
        icon: "images",
        label: "Images",
        workspaceWindow: "images",
      },
      {
        key: "automations",
        href: "/tasks",
        icon: "refresh",
        label: "Tasks",
        workspaceWindow: "automations",
      },
    ],
  },
  {
    key: "configuration",
    label: "Configuration",
    items: [
      {
        key: "models",
        href: "/settings/models",
        icon: "models",
        label: "Models",
        settingsSection: "models",
      },
      {
        key: "persona",
        href: "/settings/persona",
        icon: "persona",
        label: "Personas",
        settingsSection: "persona",
      },
      {
        key: "tools",
        href: "/settings/tools",
        icon: "tools",
        label: "Tools",
        settingsSection: "tools",
      },
      {
        key: "memory",
        href: "/settings/memory",
        icon: "memory",
        label: "Memory & Knowledge",
        settingsSection: "memory",
      },
    ],
  },
  {
    key: "security",
    label: "Security",
    items: [
      {
        key: "account",
        href: "/settings/account",
        icon: "account",
        label: "Account",
        settingsSection: "account",
      },
    ],
  },
];

function openOverlay(event: MouseEvent<HTMLAnchorElement>, item: NavigationItem) {
  if (
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return;
  }

  if (item.settingsSection) {
    event.preventDefault();
    window.dispatchEvent(
      new CustomEvent(OPEN_SETTINGS_EVENT, { detail: { section: item.settingsSection } }),
    );
    return;
  }

  if (item.workspaceWindow) {
    event.preventDefault();
    window.dispatchEvent(
      new CustomEvent(OPEN_WORKSPACE_WINDOW_EVENT, {
        detail: { window: item.workspaceWindow },
      }),
    );
  }
}

function openCommandPalette() {
  window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT));
}

export function WorkspaceBrand() {
  return (
    <Link className="workspace-brand" href="/">
      <AsterMark />
      <span>Aster</span>
    </Link>
  );
}

export function WorkspaceChrome({
  active,
  title,
}: {
  active: NavigationKey;
  title: string;
}) {
  const activeItem = NAVIGATION_SECTIONS.flatMap((section) => section.items).find(
    (item) => item.key === active,
  );

  return (
    <header className="workspace-window-bar">
      <div aria-hidden="true" className="window-controls" />
      <Link aria-label="Open chat" className="window-home" href="/">
        <AsterMark size={16} />
      </Link>
      <div className="window-tab" title={title}>
        <Icon name={activeItem?.icon ?? "chat"} size={14} />
        <span>{title}</span>
      </div>
      <button
        aria-keyshortcuts="Control+K Meta+K"
        aria-label="Open command palette"
        className="window-shortcut"
        onClick={openCommandPalette}
        title="Open command palette"
        type="button"
      >
        Ctrl K
      </button>
    </header>
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
                onClick={(event) => openOverlay(event, item)}
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
