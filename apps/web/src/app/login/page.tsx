import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { getServerAuthStatus } from "../../lib/server-api";
import { AuthForm } from "../auth-form";

export const metadata: Metadata = { title: "Sign in" };

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const status = await getServerAuthStatus();
  if (status?.setup_required) redirect("/setup");
  if (status?.authenticated) redirect("/");

  return (
    <AuthForm
      mode="login"
      initialError={status === null ? "The authentication API is unavailable." : null}
    />
  );
}
