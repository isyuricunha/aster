"use client";

import { useState, type FormEvent } from "react";

import { apiRequest, type AuthUser, type SessionRevocation } from "../../../lib/api";
import {
  SummaryCard,
  SummaryGrid,
  UnsavedBadge,
  useUnsavedChanges,
} from "../settings-primitives";
import styles from "../simple-settings.module.css";

export function AccountSettings({ username }: { username: string }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dirty = Boolean(currentPassword || newPassword || confirmation);
  useUnsavedChanges(dirty);

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
    <div aria-busy={busy !== null} className={styles.root}>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}
      {!error && notice ? <div className={styles.notice} role="status">{notice}</div> : null}

      <SummaryGrid>
        <SummaryCard label="Owner" value={username} note="Single-owner workspace" />
        <SummaryCard label="Authentication" value="Password" note="No public sign-up" />
        <SummaryCard label="Session policy" value="Private" note="Other sessions can be revoked" />
      </SummaryGrid>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Change password</h2>
            <p>Updating it signs out every other browser while keeping this session active.</p>
          </div>
          <UnsavedBadge visible={dirty} />
        </div>
        <form className={styles.sectionBody} onSubmit={changePassword}>
          <div className={styles.formGrid}>
            <label className={styles.wideField}>
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
            <label className={styles.field}>
              <span>New password</span>
              <input
                autoComplete="new-password"
                disabled={busy !== null}
                maxLength={256}
                minLength={12}
                onChange={(event) => setNewPassword(event.target.value)}
                required
                type="password"
                value={newPassword}
              />
            </label>
            <label className={styles.field}>
              <span>Confirm new password</span>
              <input
                autoComplete="new-password"
                disabled={busy !== null}
                maxLength={256}
                minLength={12}
                onChange={(event) => setConfirmation(event.target.value)}
                required
                type="password"
                value={confirmation}
              />
            </label>
          </div>
          <div className={styles.actions}>
            <button
              className={styles.primaryButton}
              disabled={busy !== null || !dirty}
              type="submit"
            >
              {busy === "password" ? "Updating password" : "Update password"}
            </button>
          </div>
        </form>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Sessions</h2>
            <p>Revoke other browsers or end the current session.</p>
          </div>
        </div>
        <div className={styles.sectionBody}>
          <div className={styles.actions}>
            <button
              className={styles.secondaryButton}
              disabled={busy !== null}
              onClick={() => void revokeSessions()}
              type="button"
            >
              {busy === "sessions" ? "Revoking sessions" : "Sign out other sessions"}
            </button>
            <button
              className={styles.dangerButton}
              disabled={busy !== null}
              onClick={() => void logout()}
              type="button"
            >
              {busy === "logout" ? "Signing out" : "Sign out here"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
