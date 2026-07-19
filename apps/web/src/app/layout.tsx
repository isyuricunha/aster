import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import "./shell.css";
import "./persona.css";
import "./chat.css";
import "./chat-controls.css";
import "./auth.css";
import "./chat-content.css";
import "./interface-refinement.css";
import "./settings-window.css";
import "./email-reader.css";
import "./command-palette.css";
import { CommandPaletteHost } from "./ui/command-palette-host";
import { WorkspaceWindowHost } from "./ui/workspace-window-host";

export const metadata: Metadata = {
  title: {
    default: "Aster",
    template: "%s · Aster",
  },
  description: "A self-hosted AI chat application",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        {children}
        <WorkspaceWindowHost />
        <CommandPaletteHost />
      </body>
    </html>
  );
}
