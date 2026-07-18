"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { apiRequest, type AuthUser } from "../lib/api";
import { AsterMark, Icon } from "./ui/icons";

export function AuthForm({
  mode,
  initialError = null,
}: {
  mode: "setup" | "login";
  initialError?: string | null;
}) {
  const setup = mode === "setup";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(initialError);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (setup && password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await apiRequest<AuthUser>(setup ? "/api/auth/setup" : "/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      window.location.assign("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Authentication failed.");
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-shell">
        <aside className="auth-context">
          <Link className="auth-brand" href="/">
            <AsterMark size={28} />
            <span>Aster</span>
          </Link>
          <div className="auth-context-copy">
            <p className="eyebrow">Private workspace</p>
            <h2>{setup ? "Your assistant, on your server." : "Welcome back to your workspace."}</h2>
            <p>
              Conversations, endpoint credentials, persona settings, and sessions remain under your
              control.
            </p>
          </div>
          <div className="auth-assurances">
            <span>
              <Icon name="lock" />
              Single-owner access
            </span>
            <span>
              <Icon name="chat" />
              Persistent private conversations
            </span>
            <span>
              <Icon name="models" />
              Your own model endpoints
            </span>
          </div>
        </aside>

        <section aria-busy={busy} className="auth-card">
          <div className="auth-card-mark">
            <AsterMark size={32} />
          </div>
          <div className="auth-heading">
            <p className="eyebrow">{setup ? "First sign-up" : "Owner access"}</p>
            <h1>{setup ? "Create the owner account" : "Sign in"}</h1>
            <p>
              {setup
                ? "This account becomes the only owner. New sign-ups close as soon as setup is complete."
                : "Use the owner account created during the first Aster setup."}
            </p>
          </div>

          {error && (
            <div className="banner banner-error" role="alert">
              {error}
            </div>
          )}

          <form className="auth-form" onSubmit={submit}>
            <label>
              <span>Username</span>
              <input
                autoCapitalize="none"
                autoComplete="username"
                autoFocus
                minLength={setup ? 3 : 1}
                maxLength={64}
                onChange={(event) => setUsername(event.target.value)}
                pattern="[A-Za-z0-9._-]+"
                placeholder="owner"
                required
                value={username}
              />
            </label>
            <label>
              <span>Password</span>
              <input
                autoComplete={setup ? "new-password" : "current-password"}
                minLength={setup ? 12 : 1}
                maxLength={256}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={setup ? "At least 12 characters" : "Enter your password"}
                required
                type="password"
                value={password}
              />
            </label>
            {setup && (
              <label>
                <span>Confirm password</span>
                <input
                  autoComplete="new-password"
                  minLength={12}
                  maxLength={256}
                  onChange={(event) => setConfirmation(event.target.value)}
                  placeholder="Repeat the password"
                  required
                  type="password"
                  value={confirmation}
                />
              </label>
            )}
            <button className="button auth-submit" disabled={busy} type="submit">
              {busy ? (setup ? "Creating owner" : "Signing in") : setup ? "Create owner" : "Sign in"}
              {!busy && <Icon name="arrow-up" size={14} />}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}
