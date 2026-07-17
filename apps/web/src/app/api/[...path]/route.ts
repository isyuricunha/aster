import type { NextRequest } from "next/server";

const internalApiBaseUrl = process.env.ASTER_API_INTERNAL_URL ?? "http://localhost:8000";
const forwardedRequestHeaders = [
  "content-type",
  "cookie",
  "idempotency-key",
  "origin",
  "user-agent",
  "x-aster-delivery",
  "x-aster-webhook-token",
  "x-forwarded-for",
  "x-real-ip",
];
const excludedResponseHeaders = new Set([
  "connection",
  "content-length",
  "keep-alive",
  "transfer-encoding",
]);

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxyRequest(request: NextRequest, context: RouteContext): Promise<Response> {
  const { path } = await context.params;
  const upstreamUrl = new URL(`/api/${path.join("/")}`, internalApiBaseUrl);
  upstreamUrl.search = request.nextUrl.search;

  const requestHeaders = new Headers();
  for (const name of forwardedRequestHeaders) {
    const value = request.headers.get(name);
    if (value) requestHeaders.set(name, value);
  }

  const body = request.method === "GET" || request.method === "HEAD" ? undefined : request.body;
  const upstream = await fetch(upstreamUrl, {
    method: request.method,
    headers: requestHeaders,
    body,
    cache: "no-store",
    redirect: "manual",
    duplex: body ? "half" : undefined,
  } as RequestInit & { duplex?: "half" });

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, name) => {
    if (!excludedResponseHeaders.has(name.toLowerCase())) {
      responseHeaders.append(name, value);
    }
  });

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const dynamic = "force-dynamic";

export function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function PATCH(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
