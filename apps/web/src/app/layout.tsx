import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import "./persona.css";

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
