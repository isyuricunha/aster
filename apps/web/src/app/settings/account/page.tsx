import { requireServerAuth } from "../../../lib/server-api";
import { AppFrame } from "../../ui/app-frame";
import { AccountSettings } from "./account-settings";

export const dynamic = "force-dynamic";

export default async function AccountSettingsPage() {
  const status = await requireServerAuth();

  return (
    <AppFrame
      active="account"
      kicker="Security"
      title="Account"
      description="Manage the owner password and active sessions protecting this Aster installation."
    >
      <AccountSettings username={status.username ?? "owner"} />
    </AppFrame>
  );
}
