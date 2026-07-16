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
import { AsterMark, Icon } from "./ui/icons";

type StreamEvent = {
  event: string;
  data: unknown;
};

type MetaEvent = {
  operation: "send" | "edit" | "regenerate";
  conversation_id: string;
  title: string;
  replace_from_position: number | null;
  messages: ChatMessage[];
  assistant_message_id: string;
};

type DeltaEvent = { content: string };
type TerminalEvent = { message: ChatMessage };
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
  const [stopping, setStopping] = useState(false);
  const [activeAssistantId, setActiveAssistantId] = useState<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingDraft, setEditingDraft] = useState("");
  const [error, setError] = useState<string | null>(initialError);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const activeAssistantIdRef = useRef<string | null>(null);

  const primaryLabel = useMemo(() => {
    if (!preferences?.primary) return null;
    return `${preferences.primary.endpoint_name} / ${preferences.primary.model_id}`;
  }, [preferences]);

  async function refreshConversations() {
    setConversations(await apiRequest<ConversationSummary[]>("/api/conversations"));
  }

  async function refreshConversation(id: string) {
    const refreshed = await apiRequest<Conversation>(`/api/conversations/${id}`);
    setConversation(refreshed);
    return refreshed;
  }

  async function selectConversation(id: string) {
    if (streaming) return;
    setError(null);
    setEditingMessageId(null);
    try {
      await refreshConversation(id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the conversation.");
    }
  }

  function startNewChat() {
    if (streaming) return;
    setConversation(null);
    setDraft("");
    setEditingMessageId(null);
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
      activeAssistantIdRef.current = meta.assistant_message_id;
      setActiveAssistantId(meta.assistant_message_id);
      setConversation((current) => {
        const retained =
          meta.replace_from_position === null
            ? (current?.messages ?? [])
            : (current?.messages ?? []).filter(
                (message) => message.position < meta.replace_from_position!,
              );
        return {
          id: meta.conversation_id,
          title: meta.title,
          messages: [...retained, ...meta.messages],
          created_at: current?.created_at ?? meta.messages[0]?.created_at ?? new Date().toISOString(),
          updated_at: meta.messages.at(-1)?.updated_at ?? new Date().toISOString(),
        };
      });
      return;
    }

    if (event.event === "delta") {
      const delta = event.data as DeltaEvent;
      const assistantId = activeAssistantIdRef.current;
      setConversation((current) => {
        if (!current || !assistantId) return current;
        return {
          ...current,
          messages: current.messages.map((message) =>
            message.id === assistantId
              ? { ...message, content: `${message.content}${delta.content}` }
              : message,
          ),
        };
      });
      return;
    }

    if (event.event === "done" || event.event === "stopped") {
      const terminal = event.data as TerminalEvent;
      setConversation((current) => {
        if (!current) return current;
        return {
          ...current,
          messages: current.messages.map((message) =>
            message.id === terminal.message.id ? terminal.message : message,
          ),
        };
      });
      return;
    }

    if (event.event === "error") {
      const failure = event.data as ErrorEvent;
      const assistantId = activeAssistantIdRef.current;
      setError(failure.message);
      setConversation((current) => {
        if (!current || !assistantId) return current;
        return {
          ...current,
          messages: current.messages.map((message) =>
            message.id === assistantId
              ? { ...message, status: "failed", error_message: failure.message }
              : message,
          ),
        };
      });
    }
  }

  async function runStream({
    conversationId,
    path,
    body,
  }: {
    conversationId: string;
    path: string;
    body?: Record<string, string>;
  }) {
    setStreaming(true);
    setStopping(false);
    setError(null);
    activeAssistantIdRef.current = null;
    setActiveAssistantId(null);
    let operationError: unknown = null;
    try {
      const response = await fetch(apiUrl(path), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        ...(body ? { body: JSON.stringify(body) } : {}),
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
    } catch (caught) {
      operationError = caught;
      throw caught;
    } finally {
      try {
        await refreshConversation(conversationId);
        await refreshConversations();
      } catch (refreshError) {
        if (operationError === null) throw refreshError;
      }
      activeAssistantIdRef.current = null;
      setActiveAssistantId(null);
      setStreaming(false);
      setStopping(false);
      requestAnimationFrame(() => composerRef.current?.focus());
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

    setDraft("");
    try {
      const target = conversation ?? (await createConversation());
      await runStream({
        conversationId: target.id,
        path: `/api/conversations/${target.id}/messages/stream`,
        body: { content },
      });
    } catch (caught) {
      setDraft(content);
      setError(caught instanceof Error ? caught.message : "Could not send the message.");
    }
  }

  function startEditing(message: ChatMessage) {
    if (streaming || message.role !== "user") return;
    setEditingMessageId(message.id);
    setEditingDraft(message.content);
    setError(null);
  }

  async function editAndResend(event: FormEvent<HTMLFormElement>, message: ChatMessage) {
    event.preventDefault();
    if (!conversation || streaming || !editingDraft.trim()) return;
    const removesLaterMessages = conversation.messages.some(
      (candidate) => candidate.position > message.position + 1,
    );
    if (
      removesLaterMessages &&
      !window.confirm("Editing this message will replace every response and message after it. Continue?")
    ) {
      return;
    }

    const content = editingDraft;
    setEditingMessageId(null);
    try {
      await runStream({
        conversationId: conversation.id,
        path: `/api/conversations/${conversation.id}/messages/${message.id}/edit-and-resend`,
        body: { content },
      });
    } catch (caught) {
      setEditingMessageId(message.id);
      setEditingDraft(content);
      setError(caught instanceof Error ? caught.message : "Could not edit and resend the message.");
    }
  }

  async function regenerate(message: ChatMessage) {
    if (!conversation || streaming || message.role !== "assistant") return;
    const removesLaterMessages = conversation.messages.some(
      (candidate) => candidate.position > message.position,
    );
    if (
      removesLaterMessages &&
      !window.confirm("Regenerating this response will remove every message after it. Continue?")
    ) {
      return;
    }

    try {
      await runStream({
        conversationId: conversation.id,
        path: `/api/conversations/${conversation.id}/messages/${message.id}/regenerate`,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not regenerate the response.");
    }
  }

  async function stopGeneration() {
    const assistantId = activeAssistantIdRef.current;
    if (!assistantId || stopping) return;
    setStopping(true);
    setError(null);
    try {
      await apiRequest(`/api/messages/${assistantId}/stop`, { method: "POST" });
    } catch (caught) {
      setStopping(false);
      setError(caught instanceof Error ? caught.message : "Could not stop the response.");
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
          <Link className="workspace-brand" href="/">
            <AsterMark />
            <span>Aster</span>
          </Link>
          <button
            aria-label="Start a new conversation"
            className="new-chat-button"
            disabled={streaming}
            onClick={startNewChat}
            title="New conversation"
          >
            <Icon name="new-chat" />
          </button>
        </div>

        <div className="chat-navigation-item active">
          <Icon name="chat" />
          <span>Chat</span>
        </div>

        <div className="sidebar-section-heading">
          <span>Conversations</span>
          <small>{conversations.length}</small>
        </div>

        <div className="conversation-list" aria-label="Conversations">
          {conversations.length === 0 ? (
            <p className="conversation-empty">Your conversations will appear here.</p>
          ) : (
            conversations.map((item) => (
              <button
                className={`conversation-item ${conversation?.id === item.id ? "active" : ""}`}
                disabled={streaming}
                key={item.id}
                onClick={() => void selectConversation(item.id)}
              >
                <span className="conversation-icon">
                  <Icon name="chat" size={14} />
                </span>
                <span className="conversation-copy">
                  <strong>{item.title}</strong>
                  <small>{item.message_count} messages</small>
                </span>
              </button>
            ))
          )}
        </div>

        <nav className="sidebar-settings" aria-label="Configuration">
          <p>Configuration</p>
          <Link href="/settings/models">
            <Icon name="models" />
            <span>Models</span>
          </Link>
          <Link href="/settings/persona">
            <Icon name="persona" />
            <span>Persona</span>
          </Link>
          <Link href="/settings/account">
            <Icon name="account" />
            <span>Account</span>
          </Link>
        </nav>

        <div className="chat-sidebar-footer">
          <span className="workspace-state-dot" />
          <div>
            <strong>Private workspace</strong>
            <small>Stored on your server</small>
          </div>
        </div>
      </aside>

      <section className="chat-workspace">
        <header className="chat-header">
          <div className="chat-header-context">
            <span className="chat-header-section">Chat</span>
            <Icon name="chevron-right" size={13} />
            <div>
              <p className="chat-title">{conversation?.title ?? "New conversation"}</p>
              <p className="chat-model">{primaryLabel ?? "Primary model not configured"}</p>
            </div>
          </div>
          {conversation && (
            <div className="chat-actions">
              <button
                aria-label="Rename conversation"
                disabled={streaming}
                onClick={() => void renameConversation()}
                title="Rename conversation"
              >
                <Icon name="edit" />
              </button>
              <button
                aria-label="Delete conversation"
                className="danger"
                disabled={streaming}
                onClick={() => void deleteConversation()}
                title="Delete conversation"
              >
                <Icon name="trash" />
              </button>
            </div>
          )}
        </header>

        <section className="chat-transcript" aria-live="polite">
          {!conversation || conversation.messages.length === 0 ? (
            <div className="chat-welcome">
              <AsterMark size={38} />
              <p className="eyebrow">New conversation</p>
              <h1>How can Aster help?</h1>
              <p>
                Start a private conversation using your configured persona and primary model. Messages
                stay in this workspace and remain available after restarts.
              </p>
              {!primaryLabel && (
                <Link className="button" href="/settings/models">
                  <Icon name="models" />
                  Configure a primary model
                </Link>
              )}
            </div>
          ) : (
            <div className="message-stack">
              {conversation.messages.map((message) => (
                <article className={`chat-message ${message.role}`} key={message.id}>
                  <div className="message-avatar">
                    {message.role === "user" ? <span>Y</span> : <AsterMark size={26} />}
                  </div>
                  <div className="message-body">
                    <div className="message-label">
                      <span>{message.role === "user" ? "You" : "Aster"}</span>
                      {message.status === "streaming" && <small>Generating</small>}
                      {message.status === "failed" && <small className="failed">Failed</small>}
                      {message.status === "stopped" && <small>Stopped</small>}
                    </div>

                    {editingMessageId === message.id ? (
                      <form
                        className="message-edit-form"
                        onSubmit={(event) => void editAndResend(event, message)}
                      >
                        <textarea
                          autoFocus
                          onChange={(event) => setEditingDraft(event.target.value)}
                          rows={4}
                          value={editingDraft}
                        />
                        <div className="message-edit-actions">
                          <button
                            className="message-action"
                            type="button"
                            onClick={() => setEditingMessageId(null)}
                          >
                            Cancel
                          </button>
                          <button
                            className="message-action primary"
                            disabled={!editingDraft.trim()}
                            type="submit"
                          >
                            Save and resend
                          </button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <div className="message-content">
                          {message.content || (message.status === "streaming" ? "…" : "")}
                        </div>
                        {message.error_message && (
                          <p className="message-error">{message.error_message}</p>
                        )}
                        {!streaming && (
                          <div className="message-actions">
                            {message.role === "user" && message.status === "completed" && (
                              <button className="message-action" onClick={() => startEditing(message)}>
                                <Icon name="edit" size={13} />
                                Edit
                              </button>
                            )}
                            {message.role === "assistant" && message.status !== "streaming" && (
                              <button
                                className="message-action"
                                onClick={() => void regenerate(message)}
                              >
                                <Icon name="refresh" size={13} />
                                Regenerate
                              </button>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <footer className="chat-composer-wrap">
          {error && <div className="chat-error">{error}</div>}
          <form className="chat-composer" onSubmit={sendMessage}>
            <div className="composer-status">
              <span className={primaryLabel ? "configured" : ""} />
              <p>{primaryLabel ?? "Configure a primary model to start chatting"}</p>
            </div>
            <div className="composer-row">
              <textarea
                aria-label="Message"
                disabled={streaming}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder={primaryLabel ? "Message Aster…" : "Primary model required"}
                ref={composerRef}
                rows={1}
                value={draft}
              />
              {streaming ? (
                <button
                  aria-label="Stop generation"
                  className="stop-generation"
                  disabled={!activeAssistantId || stopping}
                  type="button"
                  onClick={() => void stopGeneration()}
                >
                  <Icon name="stop" />
                </button>
              ) : (
                <button
                  aria-label="Send message"
                  className="send-message"
                  disabled={!draft.trim() || !primaryLabel}
                  type="submit"
                >
                  <Icon name="arrow-up" />
                </button>
              )}
            </div>
          </form>
          <p className="composer-hint">Enter to send · Shift+Enter for a new line</p>
        </footer>
      </section>
    </div>
  );
}
