import Link from "next/link";

import type { PersonaSettings } from "../../../lib/api";
import { PersonaSettingsForm } from "./persona-settings";

const neutralPersona: PersonaSettings = {
  name: "",
  instructions: "",
  enabled: false,
  instruction_role: "developer",
  created_at: "",
  updated_at: "",
};

async function getPersona(): Promise<{ persona: PersonaSettings; error: string | null }> {
  const baseUrl = process.env.ASTER_API_INTERNAL_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${baseUrl}/api/persona`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Persona API returned HTTP ${response.status}.`);
    }
    return { persona: (await response.json()) as PersonaSettings, error: null };
  } catch (caught) {
    return {
      persona: neutralPersona,
      error: caught instanceof Error ? caught.message : "Could not load the persona.",
    };
  }
}

export default async function PersonaSettingsPage() {
  const initialData = await getPersona();

  return (
    <main className="settings-page">
      <nav className="top-nav">
        <Link className="brand" href="/">
          Aster
        </Link>
        <div className="nav-links">
          <Link href="/settings/models">Models</Link>
          <span>Persona</span>
        </div>
      </nav>

      <header className="page-header">
        <p className="eyebrow">Settings</p>
        <h1>Persona</h1>
        <p className="lead">
          Define the identity and instruction layer Aster will place before the real conversation.
          The user message remains a separate user message.
        </p>
      </header>

      <PersonaSettingsForm
        initialPersona={initialData.persona}
        initialError={initialData.error}
      />
    </main>
  );
}
