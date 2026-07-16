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
      <header>
        <p className="eyebrow">Foundation</p>
        <h1>Aster</h1>
        <p className="lead">
          The application foundation is running. Chat, persona, endpoint management, and model
          caching will be built on this baseline.
        </p>
      </header>

      <section className="grid" aria-label="System status">
        <article className="card">
          <h2>Web application</h2>
          <p>Next.js is serving the initial application shell.</p>
          <span className="status status-ok">Ready</span>
        </article>

        <article className="card">
          <h2>Application API</h2>
          <p>{apiState.message}.</p>
          <span
            className={`status ${apiState.available ? "status-ok" : "status-unavailable"}`}
          >
            {apiState.available ? "Ready" : "Unavailable"}
          </span>
        </article>
      </section>
    </main>
  );
}
