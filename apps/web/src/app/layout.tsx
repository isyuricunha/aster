import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import "./shell.css";
import "./persona.css";
import "./chat.css";
import "./chat-controls.css";
import "./auth.css";
import "./interface-refinement.css";
import "./chat-content.css";

export const metadata: Metadata = {
  title: "Aster",
  description: "A self-hosted AI chat application",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
