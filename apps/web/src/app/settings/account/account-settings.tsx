"use client";

import { useState, type FormEvent } from "react";

import { apiRequest, type AuthUser, type SessionRevocation } from "../../../lib/api";
import styles from "./account-settings.module.css";

export function AccountSettings({ username }: { username: string }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(name: string, operation: () => Promise<void>) {
    if (busy) return;
    setBusy(name);
    setNotice(null);
    setError(null);
    try {
      await operation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The operation failed.");
    } finally {
      setBusy(null);
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newPassword !== confirmation) {
      setNotice(null);
      setError("New passwords do not match.");
      return;
    }
    await run("password", async () => {
      await apiRequest<AuthUser>("/api/auth/password", {
        method: "PUT",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      setNotice("Password updated. Every other session was signed out.");
    });
  }

  async function revokeSessions() {
    await run("sessions", async () => {
      const result = await apiRequest<SessionRevocation>("/api/auth/sessions", {
        method: "DELETE",
      });
      setNotice(
        result.revoked_sessions === 1
          ? "Signed out one other session."
          : `Signed out ${result.revoked_sessions} other sessions.`,
      );
    });
  }

  async function logout() {
    await run("logout", async () => {
      await apiRequest("/api/auth/logout", { method: "POST" });
      window.location.assign("/login");
    });
  }

  return (
    <div aria-busy={busy !== null} className={`settings-stack ${styles.root}`}>
      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}
      {!error && notice && (
        <div className="banner banner-success" role="status">
          {notice}
        </div>
      )}

      <section className="panel account-summary">
        <div>
          <p className="eyebrow">Owner</p>
          <h2>{username}</h2>
          <p className="section-copy">
            Aster accepts one owner account. There is no public sign-up after the first setup.
          </p>
        </div>
        <button
          className="button button-secondary"
          disabled={busy !== null}
          onClick={() => void logout()}
          type="button"
        >
          {busy === "logout" ? "Signing out" : "Sign out"}
        </button>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Security</p>
            <h2>Change password</h2>
            <p className="section-copy">
              Changing the password revokes every existing session and keeps this browser signed in.
            </p>
          </div>
        </div>
        <form aria-busy={busy === "password"} className="form-grid" onSubmit={changePassword}>
          <label className="form-span-two">
            <span>Current password</span>
            <input
              autoComplete="current-password"
              disabled={busy !== null}
              maxLength={256}
              onChange={(event) => setCurrentPassword(event.target.value)}
              required
              type="password"
              value={currentPassword}
            />
          </label>
          <label>
            <span>New password</span>
            <input
              aria-describedby="new-password-requirements"
              autoComplete="new-password"
              disabled={busy !== null}
              minLength={12}
              maxLength={256}
              onChange={(event) => setNewPassword(event.target.value)}
              required
              type="password"
              value={newPassword}
            />
          </label>
          <label>
            <span>Confirm new password</span>
            <input
              aria-describedby="new-password-requirements"
              autoComplete="new-password"
              disabled={busy !== null}
              minLength={12}
              maxLength={256}
              onChange={(event) => setConfirmation(event.target.value)}
              required
              type="password"
              value={confirmation}
            />
          </label>
          <p className="form-help form-span-two" id="new-password-requirements">
            Use 12 to 256 characters.
          </p>
          <div className="form-actions form-span-two">
            <button className="button" disabled={busy !== null} type="submit">
              {busy === "password" ? "Updating password" : "Update password"}
            </button>
          </div>
        </form>
      </section>

      <section className="panel account-session-panel">
        <div>
          <p className="eyebrow">Sessions</p>
          <h2>Sign out other browsers</h2>
          <p className="section-copy">
            Revoke every other active session while keeping this browser signed in.
          </p>
        </div>
        <button
          className="button button-secondary"
          disabled={busy !== null}
          onClick={() => void revokeSessions()}
          type="button"
        >
          {busy === "sessions" ? "Revoking sessions" : "Sign out other sessions"}
        </button>
      </section>
    </div>
  );
}
