import Link from "next/link";

import { requireServerAuth } from "../../../lib/server-api";
import { AccountSettings } from "./account-settings";

export const dynamic = "force-dynamic";

export default async function AccountSettingsPage() {
  const status = await requireServerAuth();

  return (
    <main className="settings-page">
      <nav className="top-nav">
        <Link className="brand" href="/">
          Aster
        </Link>
        <div className="nav-links">
          <Link href="/settings/models">Models</Link>
          <Link href="/settings/persona">Persona</Link>
          <span>Account</span>
        </div>
      </nav>

      <header className="page-header">
        <p className="eyebrow">Settings</p>
        <h1>Account</h1>
        <p className="lead">
          Manage the owner password and active sessions used to protect this Aster installation.
        </p>
      </header>

      <AccountSettings username={status.username ?? "owner"} />
    </main>
  );
}
