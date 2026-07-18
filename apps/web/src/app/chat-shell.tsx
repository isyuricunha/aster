"use client";

import Link from "next/link";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";

import {
  apiRequest,
  apiUrl,
  type ChatMessage,
  type Conversation,
  type ConversationSummary,
  type ModelPreferences,
  type ToolExecution,
} from "../lib/api";
import type { MediaAsset, MessageAttachment } from "../lib/image-api";
import type { RetrievalSource } from "../lib/retrieval-api";
import { ChatImageComposer, MessageAttachments } from "./chat-image-tools";
import { RetrievalSourceList } from "./chat-retrieval-sources";
import { ToolCallList, ToolExecutionCard } from "./chat-tool-cards";
import {
  createConversationMarkdown,
  createConversationTransfer,
  downloadConversationFile,
  parseConversationTransfer,
} from "./conversation-transfer";
import { copyText, MarkdownMessage } from "./markdown-message";
import { AsterMark, Icon } from "./ui/icons";
import { WorkspaceBrand, WorkspaceNavigation } from "./ui/workspace-navigation";

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
  retrieval_sources?: RetrievalSource[];
};

type DeltaEvent = { content: string };
type TerminalEvent = { message: ChatMessage };
type ToolExecutionEvent = { execution: ToolExecution };
type ErrorEvent = { code: string; message: string };
type ImageAwareMessage = ChatMessage & { attachments?: MessageAttachment[] };

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

function upsertMessage(messages: ChatMessage[], nextMessage: ChatMessage): ChatMessage[] {
  const exists = messages.some((message) => message.id === nextMessage.id);
  if (!exists) {
    return [...messages, nextMessage].sort((left, right) => left.position - right.position);
  }
  return messages.map((message) =>
    message.id === nextMessage.id
      ? {
          ...nextMessage,
          retrieval_sources: nextMessage.retrieval_sources ?? message.retrieval_sources,
          attachments:
            (nextMessage as ImageAwareMessage).attachments ??
            (message as ImageAwareMessage).attachments,
        }
      : message,
  );
}

function upsertExecution(
  executions: ToolExecution[] | undefined,
  nextExecution: ToolExecution,
): ToolExecution[] {
  const current = executions ?? [];
  const exists = current.some((execution) => execution.id === nextExecution.id);
  return exists
    ? current.map((execution) => (execution.id === nextExecution.id ? nextExecution : execution))
    : [...current, nextExecution];
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
  const [renaming, setRenaming] = useState(false);
  const [renameDraft, setRenameDraft] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ConversationSummary[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);
  const [imageEditAsset, setImageEditAsset] = useState<MediaAsset | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const mobileCloseButtonRef = useRef<HTMLButtonElement>(null);
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  const mobileSidebarRef = useRef<HTMLElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const renameRef = useRef<HTMLInputElement>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const copiedTimerRef = useRef<number | null>(null);
  const searchTimerRef = useRef<number | null>(null);
  const searchRequestRef = useRef(0);
  const activeAssistantIdRef = useRef<string | null>(null);

  const primaryLabel = useMemo(() => {
    if (!preferences?.primary) return null;
    return `${preferences.primary.endpoint_name} / ${preferences.primary.model_id}`;
  }, [preferences]);

  const visibleConversations = searchResults ?? conversations;
  const pendingConfirmation = useMemo(
    () =>
      (conversation?.tool_executions ?? []).some(
        (execution) => execution.status === "pending_confirmation",
      ),
    [conversation],
  );

  function closeMobileSidebar(restoreFocus = true) {
    const wasOpen = mobileSidebarOpen;
    setMobileSidebarOpen(false);
    if (restoreFocus && wasOpen) {
      requestAnimationFrame(() => mobileMenuButtonRef.current?.focus());
    }
  }

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      const target = event.target;
      const isTyping =
        target instanceof HTMLElement &&
        (target.matches("input, textarea, select") || target.isContentEditable);
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    }

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    const mobileLayout = window.matchMedia("(max-width: 780px)");
    function handleLayoutChange(event: MediaQueryListEvent) {
      if (!event.matches) setMobileSidebarOpen(false);
    }

    mobileLayout.addEventListener("change", handleLayoutChange);
    return () => mobileLayout.removeEventListener("change", handleLayoutChange);
  }, []);

  useEffect(
    () => () => {
      if (copiedTimerRef.current !== null) window.clearTimeout(copiedTimerRef.current);
      if (searchTimerRef.current !== null) window.clearTimeout(searchTimerRef.current);
      searchRequestRef.current += 1;
    },
    [],
  );

  useEffect(() => {
    if (!mobileSidebarOpen) return;

    function handleNavigationKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMobileSidebarOpen(false);
        requestAnimationFrame(() => mobileMenuButtonRef.current?.focus());
        return;
      }
      if (event.key !== "Tab") return;

      const sidebar = mobileSidebarRef.current;
      if (!sidebar) return;
      const focusable = Array.from(
        sidebar.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [contenteditable="true"], [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => element.getClientRects().length > 0);
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !sidebar.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !sidebar.contains(active))) {
        event.preventDefault();
        first.focus();
      }
    }

    document.body.classList.add("mobile-navigation-open");
    window.addEventListener("keydown", handleNavigationKeyDown);
    requestAnimationFrame(() => mobileCloseButtonRef.current?.focus());
    return () => {
      document.body.classList.remove("mobile-navigation-open");
      window.removeEventListener("keydown", handleNavigationKeyDown);
    };
  }, [mobileSidebarOpen]);

  function scheduleConversationSearch(value: string) {
    setSearchQuery(value);
    const query = value.trim();
    const requestId = ++searchRequestRef.current;

    if (searchTimerRef.current !== null) {
      window.clearTimeout(searchTimerRef.current);
      searchTimerRef.current = null;
    }

    if (!query) {
      setSearchResults(null);
      setSearching(false);
      setSearchError(null);
      return;
    }

    setSearching(true);
    setSearchError(null);
    searchTimerRef.current = window.setTimeout(() => {
      void apiRequest<ConversationSummary[]>(
        `/api/conversations?query=${encodeURIComponent(query)}`,
      )
        .then((results) => {
          if (searchRequestRef.current === requestId) setSearchResults(results);
        })
        .catch((caught: unknown) => {
          if (searchRequestRef.current !== requestId) return;
          setSearchError(caught instanceof Error ? caught.message : "Could not search conversations.");
          setSearchResults([]);
        })
        .finally(() => {
          if (searchRequestRef.current === requestId) setSearching(false);
        });
    }, 220);
  }

  async function refreshConversations() {
    const refreshed = await apiRequest<ConversationSummary[]>("/api/conversations");
    setConversations(refreshed);
    if (searchQuery.trim()) scheduleConversationSearch(searchQuery);
  }

  async function refreshConversation(id: string) {
    const refreshed = await apiRequest<Conversation>(`/api/conversations/${id}`);
    setConversation(refreshed);
    return refreshed;
  }

  async function selectConversation(id: string) {
    if (streaming) return;
    closeMobileSidebar();
    setError(null);
    setEditingMessageId(null);
    setImageEditAsset(null);
    setRenaming(false);
    try {
      await refreshConversation(id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the conversation.");
    }
  }

  function startNewChat() {
    if (streaming) return;
    setMobileSidebarOpen(false);
    setConversation(null);
    setDraft("");
    setEditingMessageId(null);
    setImageEditAsset(null);
    setRenaming(false);
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

  function startRenaming() {
    if (!conversation || streaming) return;
    setRenameDraft(conversation.title);
    setRenaming(true);
    requestAnimationFrame(() => {
      renameRef.current?.focus();
      renameRef.current?.select();
    });
  }

  async function renameConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!conversation || streaming) return;
    const title = renameDraft.trim();
    if (!title) return;
    if (title === conversation.title) {
      setRenaming(false);
      return;
    }

    try {
      const updated = await apiRequest<Conversation>(`/api/conversations/${conversation.id}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      });
      setConversation(updated);
      setRenaming(false);
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
      setImageEditAsset(null);
      if (searchQuery.trim()) scheduleConversationSearch(searchQuery);
      if (remaining[0]) {
        await selectConversation(remaining[0].id);
      } else {
        setConversation(null);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the conversation.");
    }
  }

  async function copyMessage(message: ChatMessage) {
    try {
      await copyText(message.content);
      setCopiedMessageId(message.id);
      if (copiedTimerRef.current !== null) window.clearTimeout(copiedTimerRef.current);
      copiedTimerRef.current = window.setTimeout(() => setCopiedMessageId(null), 1_500);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not copy the message.");
    }
  }

  function exportConversation(format: "json" | "markdown") {
    if (!conversation || streaming) return;
    try {
      if (format === "json") {
        const transfer = createConversationTransfer(conversation);
        downloadConversationFile(
          `${JSON.stringify(transfer, null, 2)}\n`,
          conversation.title,
          "aster.json",
          "application/json;charset=utf-8",
        );
        return;
      }
      downloadConversationFile(
        createConversationMarkdown(conversation),
        conversation.title,
        "md",
        "text/markdown;charset=utf-8",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not export the conversation.");
    }
  }

  async function importConversation(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    input.value = "";
    if (!file || streaming) return;
    if (file.size > 10_000_000) {
      setError("Conversation exports must be smaller than 10 MB.");
      return;
    }

    try {
      const transfer = parseConversationTransfer(await file.text());
      const imported = await apiRequest<Conversation>("/api/conversations/import", {
        method: "POST",
        body: JSON.stringify(transfer),
      });
      scheduleConversationSearch("");
      setConversation(imported);
      setEditingMessageId(null);
      setImageEditAsset(null);
      setRenaming(false);
      setError(null);
      setMobileSidebarOpen(false);
      await refreshConversations();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not import the conversation.");
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
        const incoming = meta.messages.map((message) =>
          message.id === meta.assistant_message_id
            ? { ...message, retrieval_sources: meta.retrieval_sources ?? [] }
            : message,
        );
        return {
          id: meta.conversation_id,
          title: meta.title,
          persona: current?.persona ?? null,
          retrieval: current?.retrieval,
          messages: [...retained, ...incoming],
          tool_executions: current?.tool_executions ?? [],
          created_at:
            current?.created_at ?? meta.messages[0]?.created_at ?? new Date().toISOString(),
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

    if (event.event === "assistant_started" || event.event === "tool_calls") {
      const terminal = event.data as TerminalEvent;
      if (event.event === "assistant_started") {
        activeAssistantIdRef.current = terminal.message.id;
        setActiveAssistantId(terminal.message.id);
      }
      setConversation((current) =>
        current
          ? { ...current, messages: upsertMessage(current.messages, terminal.message) }
          : current,
      );
      return;
    }

    if (event.event === "confirmation_required" || event.event === "tool_result") {
      const toolEvent = event.data as ToolExecutionEvent;
      setConversation((current) =>
        current
          ? {
              ...current,
              tool_executions: upsertExecution(current.tool_executions, toolEvent.execution),
            }
          : current,
      );
      return;
    }

    if (event.event === "done" || event.event === "stopped") {
      const terminal = event.data as TerminalEvent;
      setConversation((current) => {
        if (!current) return current;
        return {
          ...current,
          messages: upsertMessage(current.messages, terminal.message),
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
    body?: Record<string, unknown>;
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
    if (!content.trim() || streaming || pendingConfirmation) return;
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
    if (streaming || pendingConfirmation || message.role !== "user") return;
    setEditingMessageId(message.id);
    setEditingDraft(message.content);
    setError(null);
  }

  async function editAndResend(event: FormEvent<HTMLFormElement>, message: ChatMessage) {
    event.preventDefault();
    if (!conversation || streaming || pendingConfirmation || !editingDraft.trim()) return;
    const removesLaterMessages = conversation.messages.some(
      (candidate) => candidate.position > message.position + 1,
    );
    if (
      removesLaterMessages &&
      !window.confirm(
        "Editing this message will replace every response and message after it. Continue?",
      )
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
    if (!conversation || streaming || pendingConfirmation || message.role !== "assistant") return;
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

  async function decideTool(execution: ToolExecution, decision: "approve" | "deny") {
    if (!conversation || streaming) return;
    try {
      await runStream({
        conversationId: conversation.id,
        path: `/api/tool-executions/${execution.id}/${decision}`,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not ${decision} the tool call.`);
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

  function handleComposerKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function handleSearchKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      scheduleConversationSearch("");
      event.currentTarget.blur();
      return;
    }
    if (event.key === "Enter" && visibleConversations[0] && !streaming) {
      event.preventDefault();
      void selectConversation(visibleConversations[0].id);
    }
  }

  return (
    <div className="chat-app">
      {!mobileSidebarOpen ? (
        <a className="skip-link" href="#main-content">
          Skip to conversation
        </a>
      ) : null}
      {mobileSidebarOpen ? (
        <button
          aria-label="Close workspace navigation"
          className="chat-sidebar-backdrop"
          onClick={() => closeMobileSidebar()}
          tabIndex={-1}
          type="button"
        />
      ) : null}
      <aside
        aria-label="Workspace and conversations"
        aria-modal={mobileSidebarOpen ? true : undefined}
        className={`chat-sidebar ${mobileSidebarOpen ? "mobile-open" : ""}`}
        id="chat-sidebar"
        ref={mobileSidebarRef}
        role={mobileSidebarOpen ? "dialog" : undefined}
      >
        <div className="sidebar-header">
          <WorkspaceBrand />
          <button
            aria-label="Close workspace navigation"
            className="close-mobile-sidebar"
            onClick={() => closeMobileSidebar()}
            ref={mobileCloseButtonRef}
            type="button"
          >
            <Icon name="close" />
          </button>
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

        <WorkspaceNavigation
          active="chat"
          className="chat-global-navigation"
          sections={["workspace"]}
        />

        <div className="conversation-search">
          <Icon name="search" size={14} />
          <input
            aria-label="Search conversations"
            onChange={(event) => scheduleConversationSearch(event.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder="Search conversations"
            ref={searchRef}
            value={searchQuery}
          />
          {searchQuery ? (
            <button
              aria-label="Clear search"
              onClick={() => scheduleConversationSearch("")}
              type="button"
            >
              <Icon name="close" size={13} />
            </button>
          ) : (
            <kbd>/</kbd>
          )}
        </div>

        <div className="sidebar-section-heading">
          <span>{searchQuery.trim() ? "Search results" : "Conversations"}</span>
          <div className="sidebar-section-actions">
            <small>{searching ? "…" : visibleConversations.length}</small>
            <button
              aria-label="Import conversation"
              disabled={streaming}
              onClick={() => importRef.current?.click()}
              title="Import Aster conversation"
              type="button"
            >
              <Icon name="upload" size={13} />
            </button>
            <input
              accept=".json,application/json"
              className="conversation-import-input"
              onChange={(event) => void importConversation(event)}
              ref={importRef}
              type="file"
            />
          </div>
        </div>

        <div className="conversation-list" aria-label="Conversations">
          {searchError ? (
            <p className="conversation-empty conversation-search-error">{searchError}</p>
          ) : visibleConversations.length === 0 ? (
            <p className="conversation-empty">
              {searchQuery.trim()
                ? "No conversations match this search."
                : "Your conversations will appear here."}
            </p>
          ) : (
            visibleConversations.map((item) => (
              <button
                aria-pressed={conversation?.id === item.id}
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

        <WorkspaceNavigation
          active="chat"
          className="sidebar-settings"
          label="Settings navigation"
          sections={["configuration", "security"]}
        />

        <div className="chat-sidebar-footer">
          <span className="workspace-state-dot" />
          <div>
            <strong>Private workspace</strong>
            <small>Stored on your server</small>
          </div>
        </div>
      </aside>

      <main
        aria-hidden={mobileSidebarOpen ? true : undefined}
        className="chat-workspace"
        inert={mobileSidebarOpen ? true : undefined}
      >
        <header className="chat-header">
          <button
            aria-controls="chat-sidebar"
            aria-expanded={mobileSidebarOpen}
            aria-label="Open workspace navigation"
            className="open-mobile-sidebar"
            onClick={() => setMobileSidebarOpen(true)}
            ref={mobileMenuButtonRef}
            type="button"
          >
            <Icon name="menu" />
          </button>
          <div className="chat-header-context">
            <span className="chat-header-section">Chat</span>
            <Icon name="chevron-right" size={13} />
            {renaming && conversation ? (
              <form
                className="chat-title-editor"
                onSubmit={(event) => void renameConversation(event)}
              >
                <input
                  aria-label="Conversation title"
                  maxLength={200}
                  onChange={(event) => setRenameDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Escape") setRenaming(false);
                  }}
                  ref={renameRef}
                  value={renameDraft}
                />
                <button aria-label="Save title" disabled={!renameDraft.trim()} type="submit">
                  <Icon name="check" size={13} />
                </button>
                <button
                  aria-label="Cancel rename"
                  onClick={() => setRenaming(false)}
                  type="button"
                >
                  <Icon name="close" size={13} />
                </button>
              </form>
            ) : (
              <div>
                {conversation ? (
                  <h1 className="chat-title">{conversation.title}</h1>
                ) : (
                  <p className="chat-title">New conversation</p>
                )}
                <p className="chat-model">{primaryLabel ?? "Primary model not configured"}</p>
              </div>
            )}
          </div>
          {conversation && (
            <div className="chat-actions">
              <button
                aria-label="Export conversation as Markdown"
                disabled={streaming}
                onClick={() => exportConversation("markdown")}
                title="Export as Markdown"
              >
                <Icon name="download" />
              </button>
              <button
                aria-label="Export conversation as Aster JSON"
                disabled={streaming}
                onClick={() => exportConversation("json")}
                title="Export for import"
              >
                <Icon name="copy" />
              </button>
              <button
                aria-label="Rename conversation"
                disabled={streaming}
                onClick={startRenaming}
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

        <p aria-live="polite" className="sr-only" role="status">
          {stopping
            ? "Stopping the current response."
            : streaming
              ? "Aster is generating a response."
              : "Conversation ready."}
        </p>

        <section
          aria-busy={streaming}
          aria-label="Conversation"
          className="chat-transcript"
          id="main-content"
          tabIndex={-1}
        >
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
              {conversation.messages.map((message) => {
                const attachments = (message as ImageAwareMessage).attachments ?? [];
                const executions = (conversation.tool_executions ?? []).filter(
                  (execution) => execution.assistant_message_id === message.id,
                );
                return (
                  <article className={`chat-message ${message.role}`} key={message.id}>
                    <div className="message-avatar">
                      {message.role === "user" ? (
                        <span>Y</span>
                      ) : message.role === "tool" ? (
                        <Icon name="tools" size={16} />
                      ) : (
                        <AsterMark size={26} />
                      )}
                    </div>
                    <div className="message-body">
                      <div className="message-label">
                        <span>
                          {message.role === "user"
                            ? "You"
                            : message.role === "tool"
                              ? `Tool · ${message.tool_name ?? "unknown"}`
                              : "Aster"}
                        </span>
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
                            aria-label="Edit message"
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
                          {message.tool_calls?.length ? (
                            <ToolCallList calls={message.tool_calls} />
                          ) : null}
                          {message.content ? (
                            <MarkdownMessage
                              content={message.content}
                              streaming={message.status === "streaming"}
                            />
                          ) : null}
                          <MessageAttachments
                            attachments={attachments}
                            disabled={streaming}
                            onEdit={(asset) => setImageEditAsset(asset)}
                          />
                          <RetrievalSourceList sources={message.retrieval_sources ?? []} />
                          {executions.map((execution) => (
                            <ToolExecutionCard
                              disabled={streaming}
                              execution={execution}
                              key={execution.id}
                              onDecision={(item, decision) => void decideTool(item, decision)}
                            />
                          ))}
                          {message.error_message && (
                            <p className="message-error" role="alert">
                              {message.error_message}
                            </p>
                          )}
                          {!streaming && (
                            <div className="message-actions">
                              {message.content ? (
                                <button
                                  className="message-action"
                                  onClick={() => void copyMessage(message)}
                                >
                                  <Icon
                                    name={copiedMessageId === message.id ? "check" : "copy"}
                                    size={13}
                                  />
                                  {copiedMessageId === message.id ? "Copied" : "Copy"}
                                </button>
                              ) : null}
                              {message.role === "user" &&
                                message.status === "completed" &&
                                attachments.length === 0 && (
                                  <button
                                    className="message-action"
                                    onClick={() => startEditing(message)}
                                  >
                                    <Icon name="edit" size={13} />
                                    Edit
                                  </button>
                                )}
                              {message.role === "assistant" &&
                                message.status !== "streaming" &&
                                attachments.length === 0 && (
                                  <button
                                    className="message-action"
                                    disabled={pendingConfirmation}
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
                );
              })}
            </div>
          )}
        </section>

        <footer className="chat-composer-wrap">
          {error && (
            <div className="chat-error" role="alert">
              {error}
            </div>
          )}
          {pendingConfirmation ? (
            <div className="chat-error" role="status">
              Review the pending tool request before continuing.
            </div>
          ) : null}
          <ChatImageComposer
            conversation={conversation}
            disabled={streaming || pendingConfirmation}
            editAsset={imageEditAsset}
            ensureConversation={createConversation}
            onClearEdit={() => setImageEditAsset(null)}
            onCompleted={async (conversationId) => {
              await refreshConversation(conversationId);
              await refreshConversations();
            }}
            onError={(message) => setError(message || null)}
            preferences={preferences}
          />
          <form className="chat-composer" onSubmit={sendMessage}>
            <div className="composer-status">
              <span className={primaryLabel ? "configured" : ""} />
              <p>
                {pendingConfirmation
                  ? "Tool approval required"
                  : primaryLabel ?? "Configure a primary model to start chatting"}
              </p>
            </div>
            <div className="composer-row">
              <textarea
                aria-label="Message"
                disabled={streaming || pendingConfirmation}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder={
                  pendingConfirmation
                    ? "Approve or deny the pending tool call"
                    : primaryLabel
                      ? "Message Aster…"
                      : "Primary model required"
                }
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
                  disabled={!draft.trim() || !primaryLabel || pendingConfirmation}
                  type="submit"
                >
                  <Icon name="arrow-up" />
                </button>
              )}
            </div>
          </form>
          <p className="composer-hint">
            Enter to send · Shift+Enter for a new line · Press / to search history
          </p>
        </footer>
      </main>
    </div>
  );
}
