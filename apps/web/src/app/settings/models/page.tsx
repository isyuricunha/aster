import Link from "next/link";

import type { CachedModel, ModelEndpoint, ModelPreferences } from "../../../lib/api";
import { ModelSettings } from "./model-settings";

type InitialModelSettings = {
  endpoints: ModelEndpoint[];
  models: CachedModel[];
  preferences: ModelPreferences | null;
  error: string | null;
};

async function getInitialModelSettings(): Promise<InitialModelSettings> {
  const baseUrl = process.env.ASTER_API_INTERNAL_URL ?? "http://localhost:8000";

  try {
    const [endpointResponse, modelResponse, preferenceResponse] = await Promise.all([
      fetch(`${baseUrl}/api/model-endpoints`, { cache: "no-store" }),
      fetch(`${baseUrl}/api/models`, { cache: "no-store" }),
      fetch(`${baseUrl}/api/model-preferences`, { cache: "no-store" }),
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
  const initialData = await getInitialModelSettings();

  return (
    <main className="settings-page">
      <nav className="top-nav">
        <Link className="brand" href="/">
          Aster
        </Link>
        <div className="nav-links">
          <span>Models</span>
          <Link href="/settings/persona">Persona</Link>
        </div>
      </nav>

      <header className="page-header">
        <p className="eyebrow">Settings</p>
        <h1>Models</h1>
        <p className="lead">
          Connect OpenAI-compatible APIs, keep a local model cache, and choose the default model for
          each role.
        </p>
      </header>

      <ModelSettings
        initialEndpoints={initialData.endpoints}
        initialModels={initialData.models}
        initialPreferences={initialData.preferences}
        initialError={initialData.error}
      />
    </main>
  );
}
