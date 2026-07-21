"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent,
} from "react";

import { apiRequest, type Conversation, type ConversationSummary } from "../../lib/api";
import { OPEN_COMMAND_PALETTE_EVENT } from "./command-palette-host";
import { AsterMark, Icon, type IconName } from "./icons";
import {
  OPEN_SETTINGS_EVENT,
  OPEN_WORKSPACE_WINDOW_EVENT,
  type WorkspaceWindowKey,
} from "./workspace-window-host";

const COLLAPSED_STORAGE_KEY = "aster.application-sidebar-collapsed";
const CHATS_OPEN_STORAGE_KEY = "aster.application-sidebar-chats-open";
const TOOLS_OPEN_STORAGE_KEY = "aster.application-sidebar-tools-open";
const INITIAL_CONVERSATION_LIMIT = 8;
const CONVERSATION_LIMIT_STEP = 8;
const CONVERSATIONS_CHANGED_EVENT = "aster:conversations-changed";

type ToolKey = "connections" | "skills" | "agents" | "automations" | "images";
type ActiveKey = "chat" | "email" | ToolKey | "settings" | null;

type ToolItem = {
  key: ToolKey;
  href: string;
  icon: IconName;
  label: string;
  window?: WorkspaceWindowKey;
};

type ConversationChangeEvent = CustomEvent<{ conversationId?: string }>;

const TOOL_ITEMS: readonly ToolItem[] = [
  { key: "connections", href: "/connections", icon: "tools", label: "Connections" },
  { key: "skills", href: "/skills", icon: "skills", label: "Skills" },
  { key: "agents", href: "/agents", icon: "tools", label: "Agents", window: "agents" },
  {
    key: "automations",
    href: "/tasks",
    icon: "refresh",
    label: "Tasks",
    window: "automations",
  },
  { key: "images", href: "/images", icon: "images", label: "Images", window: "images" },
];

function storedBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const value = window.localStorage.getItem(key);
  return value === null ? fallback : value === "true";
}

function activeKey(pathname: string): ActiveKey {
  if (pathname === "/") return "chat";
  if (pathname.startsWith("/email")) return "email";
  if (
    pathname.startsWith("/connections") ||
    pathname.startsWith("/discord") ||
    pathname.startsWith("/communications")
  ) {
    return "connections";
  }
  if (pathname.startsWith("/skills")) return "skills";
  if (pathname.startsWith("/agents")) return "agents";
  if (pathname.startsWith("/images")) return "images";
  if (pathname.startsWith("/tasks") || pathname.startsWith("/automations")) {
    return "automations";
  }
  if (pathname.startsWith("/settings")) return "settings";
  return null;
}

function isModifiedClick(event: MouseEvent<HTMLAnchorElement>): boolean {
  return Boolean(
    event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey,
  );
}

function isTyping(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.matches("input, textarea, select") || target.isContentEditable)
  );
}

function ownerInitial(username: string): string {
  return username.trim().slice(0, 1).toUpperCase() || "O";
}

export function ApplicationSidebarHostV2() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const routeSearch = searchParams.toString();
  const hidden =
    pathname === "/login" || pathname === "/setup" || searchParams.get("embedded") === "1";
  const currentKey = activeKey(pathname);
  const startingNew = searchParams.get("new") === "1";
  const explicitConversationId = searchParams.get("conversation");

  const [collapsed, setCollapsed] = useState(() => storedBoolean(COLLAPSED_STORAGE_KEY, false));
  const [chatsOpen, setChatsOpen] = useState(() => storedBoolean(CHATS_OPEN_STORAGE_KEY, true));
  const [toolsOpen, setToolsOpen] = useState(() => storedBoolean(TOOLS_OPEN_STORAGE_KEY, true));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [username, setUsername] = useState("Owner");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationLimit, setConversationLimit] = useState(INITIAL_CONVERSATION_LIMIT);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [createdConversationId, setCreatedConversationId] = useState<string | null>(null);

  const sidebarRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const visibleConversations = conversations.slice(0, conversationLimit);
  const remaining = Math.max(0, conversations.length - conversationLimit);
  const transientConversationId = pathname === "/" && startingNew ? createdConversationId : null;
  const newChatActive = currentKey === "chat" && startingNew && !transientConversationId;
  const activeConversationId =
    pathname === "/"
      ? transientConversationId ??
        (!startingNew ? (explicitConversationId ?? conversations[0]?.id ?? null) : null)
      : null;
  const toolSectionActive = TOOL_ITEMS.some((item) => item.key === currentKey);

  const refreshConversations = useCallback(async (): Promise<ConversationSummary[]> => {
    try {
      const refreshed = await apiRequest<ConversationSummary[]>("/api/conversations");
      setConversations(refreshed);
      setError(null);
      return refreshed;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load conversations.");
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (hidden) return;
    let active = true;
    const initialRefresh = window.setTimeout(() => void refreshConversations(), 0);
    void apiRequest<{ username: string }>("/api/auth/me")
      .then((owner) => {
        if (active) setUsername(owner.username);
      })
      .catch(() => undefined);

    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void refreshConversations();
    };
    const refreshFromEvent = (event: Event) => {
      const detail = (event as ConversationChangeEvent).detail;
      void refreshConversations().then((items) => {
        if (pathname !== "/" || !startingNew) return;
        const createdId =
          detail?.conversationId ??
          items.find((item) => item.title === "New chat" && item.message_count === 0)?.id;
        if (createdId) setCreatedConversationId(createdId);
      });
    };
    const interval = window.setInterval(
      () => void refreshConversations(),
      pathname === "/" ? 8_000 : 20_000,
    );
    document.addEventListener("visibilitychange", refreshWhenVisible);
    window.addEventListener("focus", refreshWhenVisible);
    window.addEventListener(CONVERSATIONS_CHANGED_EVENT, refreshFromEvent);
    return () => {
      active = false;
      window.clearTimeout(initialRefresh);
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
      window.removeEventListener("focus", refreshWhenVisible);
      window.removeEventListener(CONVERSATIONS_CHANGED_EVENT, refreshFromEvent);
    };
  }, [hidden, pathname, refreshConversations, startingNew]);

  useEffect(() => {
    if (hidden) {
      document.documentElement.classList.remove("aster-sidebar-collapsed");
      return;
    }
    document.documentElement.classList.toggle("aster-sidebar-collapsed", collapsed);
    window.localStorage.setItem(COLLAPSED_STORAGE_KEY, String(collapsed));
    return () => document.documentElement.classList.remove("aster-sidebar-collapsed");
  }, [collapsed, hidden]);

  useEffect(() => {
    if (!mobileOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setMobileOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const sidebar = sidebarRef.current;
      if (!sidebar) return;
      const focusable = Array.from(
        sidebar.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => element.getClientRects().length > 0);
      if (!focusable.length) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const current = document.activeElement;
      if (event.shiftKey && (current === first || !sidebar.contains(current))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (current === last || !sidebar.contains(current))) {
        event.preventDefault();
        first.focus();
      }
    }
    document.body.classList.add("application-sidebar-mobile-open");
    window.addEventListener("keydown", handleKeyDown);
    requestAnimationFrame(() => closeButtonRef.current?.focus());
    return () => {
      document.body.classList.remove("application-sidebar-mobile-open");
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [mobileOpen]);

  useEffect(() => {
    if (hidden) return;
    function handleSlash(event: KeyboardEvent) {
      if (
        event.key !== "/" ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        isTyping(event.target)
      ) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT));
    }
    window.addEventListener("keydown", handleSlash, true);
    return () => window.removeEventListener("keydown", handleSlash, true);
  }, [hidden]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setMobileOpen(false));
    return () => window.cancelAnimationFrame(frame);
  }, [pathname, routeSearch]);

  function closeMobile() {
    setMobileOpen(false);
  }

  function toggleCollapsed() {
    setCollapsed((value) => !value);
  }

  function toggleSection(
    setOpen: (value: boolean | ((current: boolean) => boolean)) => void,
    storageKey: string,
  ) {
    if (collapsed) {
      setCollapsed(false);
      setOpen(true);
      window.localStorage.setItem(storageKey, "true");
      return;
    }
    setOpen((value) => {
      const next = !value;
      window.localStorage.setItem(storageKey, String(next));
      return next;
    });
  }

  function openCommandPalette() {
    window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT));
    closeMobile();
  }

  function openSettings() {
    window.dispatchEvent(new CustomEvent(OPEN_SETTINGS_EVENT));
    closeMobile();
  }

  function openWorkspace(event: MouseEvent<HTMLAnchorElement>, item: ToolItem) {
    if (!item.window || isModifiedClick(event)) {
      closeMobile();
      return;
    }
    event.preventDefault();
    window.dispatchEvent(
      new CustomEvent(OPEN_WORKSPACE_WINDOW_EVENT, { detail: { window: item.window } }),
    );
    closeMobile();
  }

  function beginRename(conversation: ConversationSummary) {
    setRenamingId(conversation.id);
    setRenameDraft(conversation.title);
  }

  async function saveRename(conversation: ConversationSummary) {
    const title = renameDraft.trim();
    if (!title || title === conversation.title) {
      setRenamingId(null);
      return;
    }
    setBusyId(conversation.id);
    try {
      await apiRequest<Conversation>(`/api/conversations/${conversation.id}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      });
      setConversations((items) =>
        items.map((item) => (item.id === conversation.id ? { ...item, title } : item)),
      );
      setRenamingId(null);
      if (activeConversationId === conversation.id) router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not rename the conversation.");
    } finally {
      setBusyId(null);
    }
  }

  async function deleteConversation(conversation: ConversationSummary) {
    if (!window.confirm(`Delete “${conversation.title}”?`)) return;
    setBusyId(conversation.id);
    try {
      await apiRequest(`/api/conversations/${conversation.id}`, { method: "DELETE" });
      setConversations((items) => items.filter((item) => item.id !== conversation.id));
      if (activeConversationId === conversation.id) router.push("/?new=1");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the conversation.");
    } finally {
      setBusyId(null);
    }
  }

  function handleRenameKeyDown(
    event: ReactKeyboardEvent<HTMLInputElement>,
    conversation: ConversationSummary,
  ) {
    if (event.key === "Escape") {
      event.preventDefault();
      setRenamingId(null);
    } else if (event.key === "Enter") {
      event.preventDefault();
      void saveRename(conversation);
    }
  }

  if (hidden) return null;

  return (
    <>
      <button
        aria-label="Open application navigation"
        className="application-sidebar-mobile-trigger"
        onClick={() => setMobileOpen(true)}
        type="button"
      >
        <Icon name="menu" size={16} />
      </button>

      {mobileOpen ? (
        <button
          aria-label="Close application navigation"
          className="application-sidebar-backdrop"
          onClick={closeMobile}
          tabIndex={-1}
          type="button"
        />
      ) : null}

      <aside
        aria-label="Application navigation"
        aria-modal={mobileOpen ? true : undefined}
        className={`unified-application-sidebar ${collapsed ? "is-collapsed" : ""} ${
          mobileOpen ? "mobile-open" : ""
        }`}
        ref={sidebarRef}
        role={mobileOpen ? "dialog" : undefined}
      >
        <header className="unified-sidebar-header">
          <Link
            aria-label="Open chat"
            className="unified-sidebar-brand"
            href="/"
            onClick={closeMobile}
          >
            <AsterMark size={22} />
            <span className="sidebar-label">Aster</span>
          </Link>
          <button
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="unified-sidebar-icon-button sidebar-collapse-button"
            onClick={toggleCollapsed}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            type="button"
          >
            <Icon name="menu" size={15} />
          </button>
          <button
            aria-label="Close application navigation"
            className="unified-sidebar-icon-button sidebar-mobile-close"
            onClick={closeMobile}
            ref={closeButtonRef}
            type="button"
          >
            <Icon name="close" size={15} />
          </button>
        </header>

        <nav aria-label="Primary" className="unified-sidebar-primary">
          <Link
            aria-current={newChatActive ? "page" : undefined}
            className="unified-sidebar-row"
            href="/?new=1"
            onClick={() => {
              setCreatedConversationId(null);
              closeMobile();
            }}
            title="New chat"
          >
            <Icon name="new-chat" size={15} />
            <span className="sidebar-label">New chat</span>
          </Link>
          <button
            className="unified-sidebar-row"
            onClick={openCommandPalette}
            title="Search"
            type="button"
          >
            <Icon name="search" size={15} />
            <span className="sidebar-label">Search</span>
            <kbd className="sidebar-label">Ctrl K</kbd>
          </button>
        </nav>

        <section className="unified-sidebar-chats">
          <div className="unified-sidebar-section-row">
            <button
              aria-controls="application-sidebar-conversations"
              aria-expanded={chatsOpen && !collapsed}
              className={`unified-sidebar-row unified-sidebar-section-toggle ${
                currentKey === "chat" && !newChatActive ? "is-active" : ""
              }`}
              onClick={() => toggleSection(setChatsOpen, CHATS_OPEN_STORAGE_KEY)}
              title="Chats"
              type="button"
            >
              <Icon name="chat" size={15} />
              <span className="sidebar-label">Chats</span>
              <span className="sidebar-label sidebar-section-count">{conversations.length}</span>
              <Icon
                className={`sidebar-label sidebar-chevron ${chatsOpen ? "is-open" : ""}`}
                name="chevron-right"
                size={13}
              />
            </button>
          </div>

          {chatsOpen && !collapsed ? (
            <div
              aria-label="Conversations"
              className="unified-sidebar-conversations"
              id="application-sidebar-conversations"
            >
              {error ? (
                <p className="unified-sidebar-status is-error">{error}</p>
              ) : loading ? (
                <p className="unified-sidebar-status">Loading conversations…</p>
              ) : visibleConversations.length === 0 ? (
                <p className="unified-sidebar-status">Your conversations will appear here.</p>
              ) : (
                visibleConversations.map((conversation) => {
                  const isActive = activeConversationId === conversation.id;
                  const isBusy = busyId === conversation.id;
                  const isRenaming = renamingId === conversation.id;
                  return (
                    <div
                      className={`unified-conversation-row ${isActive ? "is-active" : ""}`}
                      key={conversation.id}
                    >
                      {isRenaming ? (
                        <input
                          aria-label={`Rename ${conversation.title}`}
                          autoFocus
                          className="unified-conversation-rename"
                          disabled={isBusy}
                          maxLength={200}
                          onBlur={() => void saveRename(conversation)}
                          onChange={(event) => setRenameDraft(event.target.value)}
                          onKeyDown={(event) => handleRenameKeyDown(event, conversation)}
                          value={renameDraft}
                        />
                      ) : (
                        <Link
                          aria-current={isActive ? "page" : undefined}
                          className="unified-conversation-link"
                          href={`/?conversation=${encodeURIComponent(conversation.id)}`}
                          onClick={() => {
                            setCreatedConversationId(null);
                            closeMobile();
                          }}
                          title={conversation.title}
                        >
                          <span className="unified-conversation-dot" />
                          <span>{conversation.title}</span>
                        </Link>
                      )}
                      {!isRenaming ? (
                        <div className="unified-conversation-actions">
                          <button
                            aria-label={`Rename ${conversation.title}`}
                            disabled={isBusy}
                            onClick={() => beginRename(conversation)}
                            title="Rename"
                            type="button"
                          >
                            <Icon name="edit" size={12} />
                          </button>
                          <button
                            aria-label={`Delete ${conversation.title}`}
                            disabled={isBusy}
                            onClick={() => void deleteConversation(conversation)}
                            title="Delete"
                            type="button"
                          >
                            <Icon name="trash" size={12} />
                          </button>
                        </div>
                      ) : null}
                    </div>
                  );
                })
              )}

              {remaining > 0 ? (
                <button
                  className="unified-sidebar-show-more"
                  onClick={() => setConversationLimit((value) => value + CONVERSATION_LIMIT_STEP)}
                  type="button"
                >
                  Show {Math.min(CONVERSATION_LIMIT_STEP, remaining)} more
                </button>
              ) : conversations.length > INITIAL_CONVERSATION_LIMIT ? (
                <button
                  className="unified-sidebar-show-more"
                  onClick={() => setConversationLimit(INITIAL_CONVERSATION_LIMIT)}
                  type="button"
                >
                  Show less
                </button>
              ) : null}
            </div>
          ) : null}
        </section>

        <nav aria-label="Email" className="unified-sidebar-workspaces">
          <Link
            aria-current={currentKey === "email" ? "page" : undefined}
            className={`unified-sidebar-row ${currentKey === "email" ? "is-active" : ""}`}
            href="/email"
            onClick={closeMobile}
            title="Email"
          >
            <Icon name="email" size={15} />
            <span className="sidebar-label">Email</span>
          </Link>
        </nav>

        <section className="unified-sidebar-tools">
          <div className="unified-sidebar-section-row">
            <button
              aria-controls="application-sidebar-tools"
              aria-expanded={toolsOpen && !collapsed}
              className={`unified-sidebar-row unified-sidebar-section-toggle ${
                toolSectionActive ? "is-active" : ""
              }`}
              onClick={() => toggleSection(setToolsOpen, TOOLS_OPEN_STORAGE_KEY)}
              title="Tools"
              type="button"
            >
              <Icon name="tools" size={15} />
              <span className="sidebar-label">Tools</span>
              <span className="sidebar-label sidebar-section-count">{TOOL_ITEMS.length}</span>
              <Icon
                className={`sidebar-label sidebar-chevron ${toolsOpen ? "is-open" : ""}`}
                name="chevron-right"
                size={13}
              />
            </button>
          </div>
          {toolsOpen && !collapsed ? (
            <div className="unified-sidebar-tool-items" id="application-sidebar-tools">
              {TOOL_ITEMS.map((item) => (
                <Link
                  aria-current={currentKey === item.key ? "page" : undefined}
                  className={`unified-sidebar-row ${currentKey === item.key ? "is-active" : ""}`}
                  href={item.href}
                  key={item.key}
                  onClick={(event) => openWorkspace(event, item)}
                  title={item.label}
                >
                  <Icon name={item.icon} size={14} />
                  <span className="sidebar-label">{item.label}</span>
                </Link>
              ))}
            </div>
          ) : null}
        </section>

        <footer className="unified-sidebar-footer">
          <button
            aria-label="Open account settings"
            className={`unified-sidebar-owner ${currentKey === "settings" ? "is-active" : ""}`}
            onClick={openSettings}
            title={username}
            type="button"
          >
            <span className="unified-sidebar-avatar">{ownerInitial(username)}</span>
            <span className="sidebar-label">{username}</span>
          </button>
          <button
            aria-label="Open settings"
            className="unified-sidebar-icon-button unified-sidebar-settings-button"
            onClick={openSettings}
            title="Settings"
            type="button"
          >
            <Icon name="settings" size={15} />
          </button>
        </footer>
      </aside>
    </>
  );
}
