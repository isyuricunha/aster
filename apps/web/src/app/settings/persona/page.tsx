import type { Metadata } from "next";

import type {
  ConversationSummary,
  Persona,
  PersonaPreferences,
} from "../../../lib/api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { AdvancedSettings } from "../settings-primitives";
import { PersonaSettingsForm } from "./persona-settings";
import { SimplePersonaSettings } from "./simple-persona-settings";

export const metadata: Metadata = { title: "Persona settings" };

export const dynamic = "force-dynamic";

type PersonaPageData = {
  personas: Persona[];
  preferences: PersonaPreferences;
  conversations: ConversationSummary[];
  error: string | null;
};

type SettingsPageSearchParams = Promise<{ embedded?: string | string[] }>;

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

export default async function PersonaSettingsPage({
  searchParams,
}: {
  searchParams: SettingsPageSearchParams;
}) {
  await requireServerAuth();
  const [data, params] = await Promise.all([getPersonaPageData(), searchParams]);

  return (
    <AppFrame
      active="persona"
      kicker="Configuration"
      title="Personas"
      description="Create reusable identities and choose the default for new chats. Snapshot maintenance stays out of the everyday flow."
      embedded={params.embedded === "1"}
    >
      <SimplePersonaSettings
        initialError={data.error}
        initialPersonas={data.personas}
        initialPreferences={data.preferences}
      />
      <AdvancedSettings
        description="Instruction role, import and export, composition preview, duplication, deletion, and existing-conversation snapshot assignment."
      >
        <PersonaSettingsForm
          initialConversations={data.conversations}
          initialError={data.error}
          initialPersonas={data.personas}
          initialPreferences={data.preferences}
        />
      </AdvancedSettings>
    </AppFrame>
  );
}
