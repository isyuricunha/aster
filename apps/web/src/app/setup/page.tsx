import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { getServerAuthStatus } from "../../lib/server-api";
import { AuthForm } from "../auth-form";

export const metadata: Metadata = { title: "Setup" };

export const dynamic = "force-dynamic";

export default async function SetupPage() {
  const status = await getServerAuthStatus();
  if (status && !status.setup_required) {
    redirect(status.authenticated ? "/" : "/login");
  }

  return (
    <AuthForm
      mode="setup"
      initialError={status === null ? "The authentication API is unavailable." : null}
    />
  );
}
