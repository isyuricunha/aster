import type { Metadata } from "next";

import type {
  ConversationSummary,
  Persona,
  PersonaPreferences,
} from "../../../lib/api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { PersonaSettingsForm } from "./persona-settings";

export const metadata: Metadata = { title: "Persona settings" };

export const dynamic = "force-dynamic";

type PersonaPageData = {
  personas: Persona[];
  preferences: PersonaPreferences;
  conversations: ConversationSummary[];
  error: string | null;
};

async function getPersonaPageData(): Promise<PersonaPageData> {
  try {
    const [personaResponse, preferenceResponse, conversationResponse] = await Promise.all([
      serverApiFetch("/api/personas"),
      serverApiFetch("/api/persona-preferences"),
      serverApiFetch("/api/conversations"),
    ]);
    if (!personaResponse.ok || !preferenceResponse.ok || !conversationResponse.ok) {
      throw new Error("The persona API returned an error.");
    }
    return {
      personas: (await personaResponse.json()) as Persona[],
      preferences: (await preferenceResponse.json()) as PersonaPreferences,
      conversations: (await conversationResponse.json()) as ConversationSummary[],
      error: null,
    };
  } catch (caught) {
    return {
      personas: [],
      preferences: { default_persona: null },
      conversations: [],
      error: caught instanceof Error ? caught.message : "Could not load personas.",
    };
  }
}

export default async function PersonaSettingsPage() {
  await requireServerAuth();
  const data = await getPersonaPageData();

  return (
    <AppFrame
      active="persona"
      kicker="Configuration"
      title="Personas"
      description="Build reusable assistant identities, choose the default for new chats, and freeze a persona snapshot into each conversation."
    >
      <PersonaSettingsForm
        initialConversations={data.conversations}
        initialError={data.error}
        initialPersonas={data.personas}
        initialPreferences={data.preferences}
      />
    </AppFrame>
  );
}
