import type { Metadata } from "next";

import type {
  CachedModel,
  ModelEndpoint,
  ModelPreferences,
  ModelRouting,
} from "../../../lib/api";
import type { RetrievalPreferences } from "../../../lib/retrieval-api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AdvancedSettings } from "../settings-primitives";
import { AppFrame } from "../../ui/app-frame";
import { ModelProfileSettings } from "./model-profile-settings";
import { ModelSettings } from "./model-settings";
import { SimpleModelSettings } from "./simple-model-settings";

export const metadata: Metadata = { title: "Model settings" };

export const dynamic = "force-dynamic";

type InitialModelSettings = {
  endpoints: ModelEndpoint[];
  models: CachedModel[];
  preferences: ModelPreferences | null;
  retrievalPreferences: RetrievalPreferences;
  routing: ModelRouting;
  error: string | null;
};

type SettingsPageSearchParams = Promise<{ embedded?: string | string[] }>;

async function getInitialModelSettings(): Promise<InitialModelSettings> {
  try {
    const [endpointResponse, modelResponse, preferenceResponse, retrievalResponse, routingResponse] =
      await Promise.all([
        serverApiFetch("/api/model-endpoints"),
        serverApiFetch("/api/models"),
        serverApiFetch("/api/model-preferences"),
        serverApiFetch("/api/retrieval-preferences"),
        serverApiFetch("/api/model-routing"),
      ]);
    if (
      !endpointResponse.ok ||
      !modelResponse.ok ||
      !preferenceResponse.ok ||
      !retrievalResponse.ok ||
      !routingResponse.ok
    ) {
      throw new Error("The model settings API returned an error.");
    }

    return {
      endpoints: (await endpointResponse.json()) as ModelEndpoint[],
      models: (await modelResponse.json()) as CachedModel[],
      preferences: (await preferenceResponse.json()) as ModelPreferences,
      retrievalPreferences: (await retrievalResponse.json()) as RetrievalPreferences,
      routing: (await routingResponse.json()) as ModelRouting,
      error: null,
    };
  } catch (caught) {
    return {
      endpoints: [],
      models: [],
      preferences: null,
      retrievalPreferences: { embedding_model: null },
      routing: { fallbacks: [] },
      error: caught instanceof Error ? caught.message : "Could not load model settings.",
    };
  }
}

export default async function ModelsSettingsPage({
  searchParams,
}: {
  searchParams: SettingsPageSearchParams;
}) {
  await requireServerAuth();
  const [initialData, params] = await Promise.all([getInitialModelSettings(), searchParams]);

  return (
    <AppFrame
      active="models"
      kicker="Configuration"
      title="Models"
      description="Choose the connections and default models Aster uses. Technical provider overrides remain available when needed."
      embedded={params.embedded === "1"}
    >
      <SimpleModelSettings
        initialEndpoints={initialData.endpoints}
        initialError={initialData.error}
        initialModels={initialData.models}
        initialPreferences={initialData.preferences}
        initialRetrievalPreferences={initialData.retrievalPreferences}
        initialRouting={initialData.routing}
      />
      <AdvancedSettings
        description="Manual model IDs, provider parameters, capability overrides, endpoint deletion, and the complete legacy controls."
      >
        <ModelSettings
          initialEndpoints={initialData.endpoints}
          initialModels={initialData.models}
          initialPreferences={initialData.preferences}
          initialError={initialData.error}
        />
        <ModelProfileSettings
          models={initialData.models}
          preferences={initialData.preferences}
          initialRouting={initialData.routing}
        />
      </AdvancedSettings>
    </AppFrame>
  );
}
