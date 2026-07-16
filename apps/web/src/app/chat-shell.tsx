"use client";

import Link from "next/link";
import { useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import {
  apiRequest,
  apiUrl,
  type ChatMessage,
  type Conversation,
  type ConversationSummary,
  type ModelPreferences,
} from "../lib/api";

type StreamEvent = {
  event: string;
  data: unknown;
};

type MetaEvent = {
  conversation_id: string;
  title: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
};

type DeltaEvent = { content: string };
type DoneEvent = { message: ChatMessage };
type ErrorEvent = { code: string; message: string };

async function readEventStream(
  response: Response,
  handleEvent: (event: StreamEvent) => void,
): Promise<void> {
  if (!response.body) {
    throw new Error("The response stream is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  function processBlock(block: string) {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (data.length === 0) return;
    handleEvent({ event, data: JSON.parse(data.join("\n")) as unknown });
  }

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replaceAll("\r\n", "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      processBlock(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
  if (buffer.trim()) processBlock(buffer);
}

export function ChatShell({
  conversations: initialConversations,
  activeConversation: initialConversation,
  preferences,
  error: initialError,
}: {
  conversations: ConversationSummary[];
  activeConversation: Conversation | null;
  preferences: ModelPreferences | null;
  error: string | null;
}) {
  const [conversations, setConversations] = useState(initialConversations);
  const [conversation, setConversation] = useState(initialConversation);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(initialError);
  const composerRef = useRef<HTMLTextAreaElement>(null);

  const primaryLabel = useMemo(() => {
    if (!preferences?.primary) return null;
    return `${preferences.primary.endpoint_name} / ${preferences.primary.model_id}`;
  }, [preferences]);

  async function refreshConversations() {
    setConversations(await apiRequest<ConversationSummary[]>("/api/conversations"));
  }

  async function selectConversation(id: string) {
    if (streaming) return;
    setError(null);
    try {
      setConversation(await apiRequest<Conversation>(`/api/conversations/${id}`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the conversation.");
    }
  }

  function startNewChat() {
    if (streaming) return;
    setConversation(null);
    setDraft("");
    setError(null);
    requestAnimationFrame(() => composerRef.current?.focus());
  }

  async function createConversation(): Promise<Conversation> {
    const created = await apiRequest<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({}),
    });
    setConversation(created);
    await refreshConversations();
    return created;
  }

  async function renameConversation() {
    if (!conversation || streaming) return;
    const title = window.prompt("Conversation title", conversation.title)?.trim();
    if (!title || title === conversation.title) return;
    try {
      const updated = await apiRequest<Conversation>(`/api/conversations/${conversation.id}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      });
      setConversation(updated);
      await refreshConversations();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not rename the conversation.");
    }
  }

  async function deleteConversation() {
    if (!conversation || streaming) return;
    if (!window.confirm(`Delete “${conversation.title}”?`)) return;
    try {
      await apiRequest(`/api/conversations/${conversation.id}`, { method: "DELETE" });
      const remaining = conversations.filter((item) => item.id !== conversation.id);
      setConversations(remaining);
      if (remaining[0]) {
        await selectConversation(remaining[0].id);
      } else {
        setConversation(null);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the conversation.");
    }
  }

  function applyStreamEvent(event: StreamEvent) {
    if (event.event === "meta") {
      const meta = event.data as MetaEvent;
      setConversation((current) => ({
        id: meta.conversation_id,
        title: meta.title,
        messages: [...(current?.messages ?? []), meta.user_message, meta.assistant_message],
        created_at: current?.created_at ?? meta.user_message.created_at,
        updated_at: meta.assistant_message.updated_at,
      }));
      return;
    }

    if (event.event === "delta") {
      const delta = event.data as DeltaEvent;
      setConversation((current) => {
        if (!current) return current;
        return {
          ...current,
          messages: current.messages.map((message, index) =>
            index === current.messages.length - 1 && message.role === "assistant"
              ? { ...message, content: `${message.content}${delta.content}` }
              : message,
          ),
        };
      });
      return;
    }

    if (event.event === "done") {
      const done = event.data as DoneEvent;
      setConversation((current) => {
        if (!current) return current;
        return {
          ...current,
          messages: current.messages.map((message) =>
            message.id === done.message.id ? done.message : message,
          ),
        };
      });
      return;
    }

    if (event.event === "error") {
      const failure = event.data as ErrorEvent;
      setError(failure.message);
      setConversation((current) => {
        if (!current) return current;
        return {
          ...current,
          messages: current.messages.map((message, index) =>
            index === current.messages.length - 1 && message.role === "assistant"
              ? { ...message, status: "failed", error_message: failure.message }
              : message,
          ),
        };
      });
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft;
    if (!content.trim() || streaming) return;
    if (!primaryLabel) {
      setError("Configure a primary model before starting a chat.");
      return;
    }

    setStreaming(true);
    setError(null);
    setDraft("");
    try {
      const target = conversation ?? (await createConversation());
      const response = await fetch(apiUrl(`/api/conversations/${target.id}/messages/stream`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as {
          detail?: string | { message?: string };
        } | null;
        const detail = payload?.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : detail?.message ?? `Request failed with HTTP ${response.status}`,
        );
      }
      await readEventStream(response, applyStreamEvent);
      const refreshed = await apiRequest<Conversation>(`/api/conversations/${target.id}`);
      setConversation(refreshed);
      await refreshConversations();
    } catch (caught) {
      setDraft(content);
      setError(caught instanceof Error ? caught.message : "Could not send the message.");
    } finally {
      setStreaming(false);
      requestAnimationFrame(() => composerRef.current?.focus());
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className="chat-app">
      <aside className="chat-sidebar">
        <div className="sidebar-header">
          <span className="brand">Aster</span>
          <button className="new-chat-button" disabled={streaming} onClick={startNewChat}>
            New chat
          </button>
        </div>

        <div className="conversation-list" aria-label="Conversations">
          {conversations.length === 0 ? (
            <p className="conversation-empty">No conversations yet.</p>
          ) : (
            conversations.map((item) => (
              <button
                className={`conversation-item ${conversation?.id === item.id ? "active" : ""}`}
                disabled={streaming}
                key={item.id}
                onClick={() => void selectConversation(item.id)}
              >
                <span>{item.title}</span>
                <small>{item.message_count} messages</small>
              </button>
            ))
          )}
        </div>

        <nav className="sidebar-settings">
          <Link href="/settings/models">Models</Link>
          <Link href="/settings/persona">Persona</Link>
        </nav>
      </aside>

      <main className="chat-main">
        <header className="chat-header">
          <div>
            <p className="chat-title">{conversation?.title ?? "New chat"}</p>
            <p className="chat-model">{primaryLabel ?? "Primary model not configured"}</p>
          </div>
          {conversation && (
            <div className="chat-actions">
              <button disabled={streaming} onClick={() => void renameConversation()}>
                Rename
              </button>
              <button className="danger" disabled={streaming} onClick={() => void deleteConversation()}>
                Delete
              </button>
            </div>
          )}
        </header>

        <section className="chat-transcript" aria-live="polite">
          {!conversation || conversation.messages.length === 0 ? (
            <div className="chat-welcome">
              <p className="eyebrow">Persistent chat</p>
              <h1>What are we working on?</h1>
              <p>
                Messages are stored locally. The configured persona is sent as an instruction, and
                the primary model handles the response.
              </p>
              {!primaryLabel && (
                <Link className="button" href="/settings/models">
                  Configure a primary model
                </Link>
              )}
            </div>
          ) : (
            <div className="message-stack">
              {conversation.messages.map((message) => (
                <article className={`chat-message ${message.role}`} key={message.id}>
                  <div className="message-label">
                    <span>{message.role === "user" ? "You" : "Assistant"}</span>
                    {message.status === "streaming" && <small>Streaming</small>}
                    {message.status === "failed" && <small>Failed</small>}
                  </div>
                  <div className="message-content">
                    {message.content || (message.status === "streaming" ? "…" : "")}
                  </div>
                  {message.error_message && <p className="message-error">{message.error_message}</p>}
                </article>
              ))}
            </div>
          )}
        </section>

        <footer className="chat-composer-wrap">
          {error && <div className="chat-error">{error}</div>}
          <form className="chat-composer" onSubmit={sendMessage}>
            <textarea
              aria-label="Message"
              disabled={streaming}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder={primaryLabel ? "Message Aster" : "Configure a primary model first"}
              ref={composerRef}
              rows={1}
              value={draft}
            />
            <button disabled={streaming || !draft.trim() || !primaryLabel} type="submit">
              {streaming ? "Sending" : "Send"}
            </button>
          </form>
          <p className="composer-hint">Enter to send · Shift+Enter for a new line</p>
        </footer>
      </main>
    </div>
  );
}
