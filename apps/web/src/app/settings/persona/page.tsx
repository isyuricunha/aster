import type { PersonaSettings } from "../../../lib/api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { PersonaSettingsForm } from "./persona-settings";

export const dynamic = "force-dynamic";

const neutralPersona: PersonaSettings = {
  name: "",
  instructions: "",
  enabled: false,
  instruction_role: "developer",
  created_at: "",
  updated_at: "",
};

async function getPersona(): Promise<{ persona: PersonaSettings; error: string | null }> {
  try {
    const response = await serverApiFetch("/api/persona");
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
  await requireServerAuth();
  const initialData = await getPersona();

  return (
    <AppFrame
      active="persona"
      kicker="Configuration"
      title="Persona"
      description="Define the identity and instruction layer applied before the real conversation while preserving the user message as its own role."
    >
      <PersonaSettingsForm
        initialPersona={initialData.persona}
        initialError={initialData.error}
      />
    </AppFrame>
  );
}
