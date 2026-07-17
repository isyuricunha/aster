import type {
  CachedModel,
  ModelEndpoint,
  ModelPreferences,
  ModelRouting,
} from "../../../lib/api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { ModelProfileSettings } from "./model-profile-settings";
import { ModelSettings } from "./model-settings";

export const dynamic = "force-dynamic";

type InitialModelSettings = {
  endpoints: ModelEndpoint[];
  models: CachedModel[];
  preferences: ModelPreferences | null;
  routing: ModelRouting;
  error: string | null;
};

async function getInitialModelSettings(): Promise<InitialModelSettings> {
  try {
    const [endpointResponse, modelResponse, preferenceResponse, routingResponse] =
      await Promise.all([
        serverApiFetch("/api/model-endpoints"),
        serverApiFetch("/api/models"),
        serverApiFetch("/api/model-preferences"),
        serverApiFetch("/api/model-routing"),
      ]);

    if (
      !endpointResponse.ok ||
      !modelResponse.ok ||
      !preferenceResponse.ok ||
      !routingResponse.ok
    ) {
      throw new Error("The model settings API returned an error.");
    }

    return {
      endpoints: (await endpointResponse.json()) as ModelEndpoint[],
      models: (await modelResponse.json()) as CachedModel[],
      preferences: (await preferenceResponse.json()) as ModelPreferences,
      routing: (await routingResponse.json()) as ModelRouting,
      error: null,
    };
  } catch (caught) {
    return {
      endpoints: [],
      models: [],
      preferences: null,
      routing: { fallbacks: [] },
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
      description="Connect compatible APIs, configure model behavior, and define reliable routing across Aster."
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
    </AppFrame>
  );
}
