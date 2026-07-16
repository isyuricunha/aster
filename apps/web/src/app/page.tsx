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
        <div className="nav-links">
          <Link href="/settings/models">Models</Link>
          <Link href="/settings/persona">Persona</Link>
        </div>
      </nav>

      <header className="hero-header">
        <p className="eyebrow">Self-hosted AI</p>
        <h1>Aster</h1>
        <p className="lead">
          Model connections and user-defined identity are ready. Configure the endpoint layer, set
          the global persona, and inspect how Aster keeps instructions separate from user messages.
        </p>
        <div className="button-row hero-action">
          <Link className="button" href="/settings/models">
            Configure models
          </Link>
          <Link className="button button-secondary" href="/settings/persona">
            Configure persona
          </Link>
        </div>
      </header>

      <section className="grid" aria-label="System status">
        <article className="card">
          <h2>Model configuration</h2>
          <p>Endpoints, encrypted credentials, model caching, and default roles are available.</p>
          <span className="status status-ok">Ready</span>
        </article>

        <article className="card">
          <h2>Persona composition</h2>
          <p>Global persona settings and canonical role previews are available.</p>
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
