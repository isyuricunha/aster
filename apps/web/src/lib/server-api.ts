import { headers } from "next/headers";
import { redirect } from "next/navigation";

import type { AuthStatus } from "./api";

const internalApiBaseUrl = process.env.ASTER_API_INTERNAL_URL ?? "http://localhost:8000";

export async function serverApiFetch(path: string, init?: RequestInit): Promise<Response> {
  const incomingHeaders = await headers();
  const forwardedHeaders = new Headers(init?.headers);
  const cookie = incomingHeaders.get("cookie");
  if (cookie) {
    forwardedHeaders.set("cookie", cookie);
  }
  if (init?.body !== undefined) {
    forwardedHeaders.set("Content-Type", "application/json");
  }

  return fetch(`${internalApiBaseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: forwardedHeaders,
  });
}

export async function getServerAuthStatus(): Promise<AuthStatus | null> {
  try {
    const response = await serverApiFetch("/api/auth/status");
    if (!response.ok) return null;
    return (await response.json()) as AuthStatus;
  } catch {
    return null;
  }
}

export async function requireServerAuth(): Promise<AuthStatus> {
  const status = await getServerAuthStatus();
  if (!status) redirect("/login");
  if (status.setup_required) redirect("/setup");
  if (!status.authenticated) redirect("/login");
  return status;
}
