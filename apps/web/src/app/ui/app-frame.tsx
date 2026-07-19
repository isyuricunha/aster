import type { ReactNode } from "react";

import { Icon } from "./icons";
import {
  MobileWorkspaceNavigation,
  type NavigationKey,
  WorkspaceBrand,
  WorkspaceChrome,
  WorkspaceNavigation,
} from "./workspace-navigation";

export function AppFrame({
  active,
  kicker,
  title,
  description,
  children,
  embedded = false,
}: {
  active: NavigationKey;
  kicker: string;
  title: string;
  description: string;
  children: ReactNode;
  embedded?: boolean;
}) {
  if (embedded) {
    return (
      <main className="embedded-settings-page" id="main-content" tabIndex={-1}>
        <header className="settings-hero">
          <p>{kicker}</p>
          <h1 className="shimmer-text">{title}</h1>
          <span>{description}</span>
        </header>
        {children}
      </main>
    );
  }

  return (
    <div className="application-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <WorkspaceChrome active={active} title={title} />
      <aside className="application-sidebar">
        <WorkspaceBrand />
        <WorkspaceNavigation active={active} />

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
          <MobileWorkspaceNavigation active={active} title={title} />
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

        <main className="settings-content" id="main-content" tabIndex={-1}>
          <header className="settings-hero">
            <p>{kicker}</p>
            <h1 className="shimmer-text">{title}</h1>
            <span>{description}</span>
          </header>
          {children}
        </main>
      </div>
    </div>
  );
}
