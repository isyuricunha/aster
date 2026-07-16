"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { apiRequest, type AuthUser } from "../lib/api";

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
      <section className="auth-card">
        <Link className="brand" href="/">
          Aster
        </Link>
        <div className="auth-heading">
          <p className="eyebrow">{setup ? "First sign-up" : "Welcome back"}</p>
          <h1>{setup ? "Create the owner account" : "Sign in"}</h1>
          <p>
            {setup
              ? "This account becomes the only Aster owner. Public sign-up closes immediately after it is created."
              : "Use the owner account created during the first Aster setup."}
          </p>
        </div>

        {error && <div className="banner banner-error">{error}</div>}

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
                required
                type="password"
                value={confirmation}
              />
            </label>
          )}
          <button className="button" disabled={busy} type="submit">
            {busy ? (setup ? "Creating owner" : "Signing in") : setup ? "Create owner" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
