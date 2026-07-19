"use client";

import { useMemo, useState } from "react";

import type {
  CommunicationMessage,
  CommunicationThreadKind,
} from "../../lib/communication-api";

function htmlDocument(content: string): string {
  return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta
      http-equiv="Content-Security-Policy"
      content="default-src 'none'; img-src data: cid:; style-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'; frame-src 'none'"
    />
    <meta name="color-scheme" content="light dark" />
    <style>
      :root { color-scheme: light dark; }
      html { background: transparent; }
      body {
        margin: 0;
        padding: 16px;
        overflow-wrap: anywhere;
        background: transparent;
        color: CanvasText;
        font: 14px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      img { max-width: 100%; height: auto; }
      table { max-width: 100%; border-collapse: collapse; }
      pre { overflow: auto; white-space: pre-wrap; }
      blockquote { margin-inline: 0; padding-inline-start: 12px; border-inline-start: 3px solid GrayText; }
      a { color: LinkText; }
    </style>
  </head>
  <body>${content}</body>
</html>`;
}

export function EmailMessageBody({
  message,
  threadKind,
}: {
  message: CommunicationMessage;
  threadKind: CommunicationThreadKind;
}) {
  const hasHtml = threadKind === "email" && Boolean(message.content_html?.trim());
  const [mode, setMode] = useState<"html" | "plain">(hasHtml ? "html" : "plain");
  const source = useMemo(
    () => (message.content_html ? htmlDocument(message.content_html) : ""),
    [message.content_html],
  );

  return (
    <div className="communication-message-body">
      {hasHtml ? (
        <div className="communication-body-toggle" role="group" aria-label="Message body format">
          <button
            aria-pressed={mode === "html"}
            className={mode === "html" ? "active" : ""}
            onClick={() => setMode("html")}
            type="button"
          >
            Email view
          </button>
          <button
            aria-pressed={mode === "plain"}
            className={mode === "plain" ? "active" : ""}
            onClick={() => setMode("plain")}
            type="button"
          >
            Plain text
          </button>
          <span>Remote content and scripts are blocked.</span>
        </div>
      ) : null}

      {mode === "html" && hasHtml ? (
        <iframe
          className="communication-html-frame"
          referrerPolicy="no-referrer"
          sandbox=""
          srcDoc={source}
          title={`Rendered email from ${message.sender_name || message.sender_address || "sender"}`}
        />
      ) : (
        <div className="communication-plain-body">
          {message.content_text || "No plain-text content"}
        </div>
      )}
    </div>
  );
}
