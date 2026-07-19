import type { Metadata } from "next";

import { requireServerAuth } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { AccountSettings } from "./account-settings";

export const metadata: Metadata = { title: "Account settings" };

export const dynamic = "force-dynamic";

type SettingsPageSearchParams = Promise<{ embedded?: string | string[] }>;

export default async function AccountSettingsPage({
  searchParams,
}: {
  searchParams: SettingsPageSearchParams;
}) {
  const [status, params] = await Promise.all([requireServerAuth(), searchParams]);

  return (
    <AppFrame
      active="account"
      kicker="Security"
      title="Account"
      description="Manage the owner password and active sessions protecting this Aster installation."
      embedded={params.embedded === "1"}
    >
      <AccountSettings username={status.username ?? "owner"} />
    </AppFrame>
  );
}
