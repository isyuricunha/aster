"use client";

import { useMemo, useState } from "react";

import type {
  CommunicationMessage,
  CommunicationThreadKind,
} from "../../lib/communication-api";

const DEFAULT_ZOOM = 1.15;
const MIN_ZOOM = 0.8;
const MAX_ZOOM = 1.6;
const ZOOM_STEP = 0.1;

function boundedZoom(value: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Number(value.toFixed(2))));
}

function htmlDocument(content: string, zoom: number): string {
  const layoutWidth = (100 / zoom).toFixed(3);
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
      * { box-sizing: border-box; }
      html {
        min-height: 100%;
        overflow-x: hidden;
        background: transparent;
      }
      body {
        width: ${layoutWidth}%;
        min-height: 100%;
        margin: 0 auto;
        padding: 20px clamp(16px, 2.4vw, 30px);
        overflow-wrap: anywhere;
        background: transparent;
        color: CanvasText;
        font: 14px/1.55 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        zoom: ${zoom};
      }
      body > table,
      body > div {
        max-width: 100% !important;
        margin-inline: auto !important;
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
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);
  const source = useMemo(
    () => (message.content_html ? htmlDocument(message.content_html, zoom) : ""),
    [message.content_html, zoom],
  );

  return (
    <div className="communication-message-body">
      {hasHtml ? (
        <div className="communication-body-toggle">
          <div aria-label="Message body format" className="communication-view-switch" role="group">
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
          </div>
          <span className="communication-body-status">Remote content and scripts are blocked.</span>
          {mode === "html" ? (
            <div aria-label="Email zoom" className="communication-zoom-controls" role="group">
              <button
                aria-label="Zoom email out"
                disabled={zoom <= MIN_ZOOM}
                onClick={() => setZoom((current) => boundedZoom(current - ZOOM_STEP))}
                type="button"
              >
                −
              </button>
              <output aria-live="polite">{Math.round(zoom * 100)}%</output>
              <button
                aria-label="Zoom email in"
                disabled={zoom >= MAX_ZOOM}
                onClick={() => setZoom((current) => boundedZoom(current + ZOOM_STEP))}
                type="button"
              >
                +
              </button>
            </div>
          ) : null}
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
