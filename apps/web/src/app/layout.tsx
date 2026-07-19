import type { Metadata, Viewport } from "next";
import { Suspense, type ReactNode } from "react";

import "./globals.css";
import "./shell.css";
import "./persona.css";
import "./chat.css";
import "./chat-controls.css";
import "./auth.css";
import "./chat-content.css";
import "./chat-generation-experience.css";
import "./interface-refinement.css";
import "./settings-window.css";
import "./email-reader.css";
import "./command-palette.css";
import "./application-sidebar.css";
import { ApplicationSidebarHost } from "./ui/application-sidebar-host";
import { CommandPaletteHost } from "./ui/command-palette-host";
import { ConversationRouteSync } from "./ui/conversation-route-sync";
import { WorkspaceWindowHost } from "./ui/workspace-window-host";

export const metadata: Metadata = {
  applicationName: "Aster",
  title: {
    default: "Aster",
    template: "%s · Aster",
  },
  description: "A self-hosted AI chat application",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/brand/aster-logo.svg", type: "image/svg+xml" }],
    shortcut: "/brand/aster-logo.svg",
    apple: "/brand/aster-logo.svg",
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#060707",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        {children}
        <ConversationRouteSync />
        <Suspense fallback={null}>
          <ApplicationSidebarHost />
        </Suspense>
        <WorkspaceWindowHost />
        <CommandPaletteHost />
      </body>
    </html>
  );
}
