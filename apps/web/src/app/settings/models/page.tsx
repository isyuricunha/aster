import Link from "next/link";

import type { CachedModel, ModelEndpoint, ModelPreferences } from "../../../lib/api";
import { requireServerAuth, serverApiFetch } from "../../../lib/server-api";
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
    <main className="settings-page">
      <nav className="top-nav">
        <Link className="brand" href="/">
          Aster
        </Link>
        <div className="nav-links">
          <span>Models</span>
          <Link href="/settings/persona">Persona</Link>
          <Link href="/settings/account">Account</Link>
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
