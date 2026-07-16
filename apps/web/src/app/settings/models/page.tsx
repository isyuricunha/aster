import type { CachedModel, ModelEndpoint, ModelPreferences } from "../../../lib/api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { ModelSettings } from "./model-settings";

export const dynamic = "force-dynamic";

type InitialModelSettings = {
  endpoints: ModelEndpoint[];
  models: CachedModel[];
  preferences: ModelPreferences | null;
  error: string | null;
};

async function getInitialModelSettings(): Promise<InitialModelSettings> {
  try {
    const [endpointResponse, modelResponse, preferenceResponse] = await Promise.all([
      serverApiFetch("/api/model-endpoints"),
      serverApiFetch("/api/models"),
      serverApiFetch("/api/model-preferences"),
    ]);

    if (!endpointResponse.ok || !modelResponse.ok || !preferenceResponse.ok) {
      throw new Error("The model settings API returned an error.");
    }

    return {
      endpoints: (await endpointResponse.json()) as ModelEndpoint[],
      models: (await modelResponse.json()) as CachedModel[],
      preferences: (await preferenceResponse.json()) as ModelPreferences,
      error: null,
    };
  } catch (caught) {
    return {
      endpoints: [],
      models: [],
      preferences: null,
      error: caught instanceof Error ? caught.message : "Could not load model settings.",
    };
  }
}

export default async function ModelsSettingsPage() {
  await requireServerAuth();
  const initialData = await getInitialModelSettings();

  return (
    <AppFrame
      active="models"
      kicker="Configuration"
      title="Models"
      description="Connect compatible APIs, maintain the local model catalog, and assign the defaults used across Aster."
    >
      <ModelSettings
        initialEndpoints={initialData.endpoints}
        initialModels={initialData.models}
        initialPreferences={initialData.preferences}
        initialError={initialData.error}
      />
    </AppFrame>
  );
}
