"use client";

import { useEffect } from "react";

import { AsterMark, Icon } from "./ui/icons";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="route-state" role="alert">
      <AsterMark size={32} />
      <div>
        <p>This view could not be loaded</p>
        <span>Your data was not changed. Try loading the workspace again.</span>
      </div>
      <button className="button button-secondary" onClick={reset} type="button">
        <Icon name="refresh" size={14} />
        Try again
      </button>
    </main>
  );
}
