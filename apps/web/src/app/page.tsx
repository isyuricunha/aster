import Link from "next/link";

export const dynamic = "force-dynamic";

type ApiState = {
  available: boolean;
  message: string;
};

async function getApiState(): Promise<ApiState> {
  const baseUrl = process.env.ASTER_API_INTERNAL_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${baseUrl}/ready`, { cache: "no-store" });

    if (!response.ok) {
      return {
        available: false,
        message: `Readiness check returned HTTP ${response.status}`,
      };
    }

    return { available: true, message: "API and database are ready" };
  } catch {
    return { available: false, message: "API is currently unavailable" };
  }
}

export default async function Home() {
  const apiState = await getApiState();

  return (
    <main>
      <nav className="top-nav">
        <span className="brand">Aster</span>
        <Link href="/settings/models">Model settings</Link>
      </nav>

      <header className="hero-header">
        <p className="eyebrow">Self-hosted AI</p>
        <h1>Aster</h1>
        <p className="lead">
          The model layer is ready for configuration. Add an OpenAI-compatible endpoint, synchronize
          its model list, and choose the defaults Aster will use next.
        </p>
        <Link className="button hero-action" href="/settings/models">
          Configure models
        </Link>
      </header>

      <section className="grid" aria-label="System status">
        <article className="card">
          <h2>Model configuration</h2>
          <p>Endpoints, encrypted credentials, model caching, and default roles are available.</p>
          <span className="status status-ok">Ready</span>
        </article>

        <article className="card">
          <h2>Application API</h2>
          <p>{apiState.message}.</p>
          <span className={`status ${apiState.available ? "status-ok" : "status-unavailable"}`}>
            {apiState.available ? "Ready" : "Unavailable"}
          </span>
        </article>
      </section>
    </main>
  );
}
