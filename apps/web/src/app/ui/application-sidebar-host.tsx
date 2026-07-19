"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent,
} from "react";

import {
  apiRequest,
  type Conversation,
  type ConversationSummary,
} from "../../lib/api";
import { parseConversationTransfer } from "../conversation-transfer";
import { OPEN_COMMAND_PALETTE_EVENT } from "./command-palette-host";
import { AsterMark, Icon, type IconName } from "./icons";
import {
  OPEN_SETTINGS_EVENT,
  OPEN_WORKSPACE_WINDOW_EVENT,
  type WorkspaceWindowKey,
} from "./workspace-window-host";

const COLLAPSED_STORAGE_KEY = "aster.application-sidebar-collapsed";
const CHATS_OPEN_STORAGE_KEY = "aster.application-sidebar-chats-open";
const INITIAL_CONVERSATION_LIMIT = 8;
const CONVERSATION_LIMIT_STEP = 8;

const WORKSPACE_ITEMS: readonly {
  key: WorkspaceWindowKey;
  href: string;
  icon: IconName;
  label: string;
}[] = [
  {
    key: "communications",
    href: "/communications",
    icon: "chat",
    label: "Communications",
  },
  { key: "agents", href: "/agents", icon: "tools", label: "Agents" },
  { key: "images", href: "/images", icon: "images", label: "Images" },
  {
    key: "automations",
    href: "/automations",
    icon: "refresh",
    label: "Automations",
  },
];

type WorkspaceActiveKey = "chat" | WorkspaceWindowKey | "settings" | null;

function readStoredBoolean(key: string, fallback: boolean): boolean {
  if (typeof window === "undefined") return fallback;
  const stored = window.localStorage.getItem(key);
  if (stored === null) return fallback;
  return stored === "true";
}

function activeKeyForPath(pathname: string): WorkspaceActiveKey {
  if (pathname === "/") return "chat";
  if (pathname.startsWith("/communications")) return "communications";
  if (pathname.startsWith("/agents")) return "agents";
  if (pathname.startsWith("/images")) return "images";
  if (pathname.startsWith("/automations")) return "automations";
  if (pathname.startsWith("/settings")) return "settings";
  return null;
}

function isModifiedClick(event: MouseEvent<HTMLAnchorElement>): boolean {
  return (
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  );
}

function ownerInitial(username: string): string {
  return username.trim().slice(0, 1).toUpperCase() || "O";
}

function isTypingTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.matches("input, textarea, select") || target.isContentEditable)
  );
}

export function ApplicationSidebarHost() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const embedded = searchParams.get("embedded") === "1";
  const hiddenRoute = pathname === "/login" || pathname === "/setup" || embedded;
  const activeKey = activeKeyForPath(pathname);
  const explicitConversationId = searchParams.get("conversation");
  const startingNewConversation = searchParams.get("new") === "1";

  const [collapsed, setCollapsed] = useState(() =>
    readStoredBoolean(COLLAPSED_STORAGE_KEY, false),
  );
  const [chatsOpen, setChatsOpen] = useState(() =>
    readStoredBoolean(CHATS_OPEN_STORAGE_KEY, true),
  );
  const [mobileOpen, setMobileOpen] = useState(false);
  const [username, setUsername] = useState("Owner");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationLimit, setConversationLimit] = useState(INITIAL_CONVERSATION_LIMIT);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [conversationError, setConversationError] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [busyConversationId, setBusyConversationId] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  const sidebarRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const importRef = useRef<HTMLInputElement>(null);

  const visibleConversations = conversations.slice(0, conversationLimit);
  const remainingConversationCount = Math.max(0, conversations.length - conversationLimit);
  const activeConversationId =
    pathname === "/" && !startingNewConversation
      ? explicitConversationId ?? conversations[0]?.id ?? null
      : null;

  const refreshConversations = useCallback(async () => {
    try {
      const next = await apiRequest<ConversationSummary[]>("/api/conversations");
      setConversations(next);
      setConversationError(null);
    } catch (caught) {
      setConversationError(
        caught instanceof Error ? caught.message : "Could not load conversations.",
      );
    } finally {
      setLoadingConversations(false);
    }
  }, []);

  useEffect(() => {
    if (hiddenRoute) return;

    let active = true;
    void apiRequest<{ username: string }>("/api/auth/me")
      .then((owner) => {
        if (active) setUsername(owner.username);
      })
      .catch(() => undefined);
    void refreshConversations();

    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void refreshConversations();
    };
    const refreshOnFocus = () => void refreshConversations();
    const interval = window.setInterval(
      () => void refreshConversations(),
      pathname === "/" ? 8_000 : 20_000,
    );

    document.addEventListener("visibilitychange", refreshWhenVisible);
    window.addEventListener("focus", refreshOnFocus);
    window.addEventListener("aster:conversations-changed", refreshOnFocus);
    return () => {
      active = false;
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
      window.removeEventListener("focus", refreshOnFocus);
      window.removeEventListener("aster:conversations-changed", refreshOnFocus);
    };
  }, [hiddenRoute, pathname, refreshConversations]);

  useEffect(() => {
    if (hiddenRoute) {
      document.documentElement.classList.remove("aster-sidebar-collapsed");
      return;
    }
    document.documentElement.classList.toggle("aster-sidebar-collapsed", collapsed);
    window.localStorage.setItem(COLLAPSED_STORAGE_KEY, String(collapsed));
    return () => document.documentElement.classList.remove("aster-sidebar-collapsed");
  }, [collapsed, hiddenRoute]);

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
      if (focusable.length === 0) {
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
    if (hiddenRoute) return;
    function handleSlash(event: KeyboardEvent) {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
      if (isTypingTarget(event.target)) return;
      event.preventDefault();
      event.stopPropagation();
      window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT));
    }
    window.addEventListener("keydown", handleSlash, true);
    return () => window.removeEventListener("keydown", handleSlash, true);
  }, [hiddenRoute]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname, searchParams]);

  const workspaceItems = useMemo(
    () =>
      WORKSPACE_ITEMS.map((item) => ({
        ...item,
        active: activeKey === item.key,
      })),
    [activeKey],
  );

  function closeMobile() {
    setMobileOpen(false);
  }

  function toggleCollapsed() {
    setCollapsed((current) => !current);
  }

  function toggleChats() {
    if (collapsed) {
      setCollapsed(false);
      setChatsOpen(true);
      window.localStorage.setItem(CHATS_OPEN_STORAGE_KEY, "true");
      return;
    }
    setChatsOpen((current) => {
      const next = !current;
      window.localStorage.setItem(CHATS_OPEN_STORAGE_KEY, String(next));
      return next;
    });
  }

  function openCommandPalette() {
    window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT));
    closeMobile();
  }

  function openSettings(section?: "account") {
    window.dispatchEvent(
      new CustomEvent(OPEN_SETTINGS_EVENT, {
        detail: section ? { section } : undefined,
      }),
    );
    closeMobile();
  }

  function openWorkspace(
    event: MouseEvent<HTMLAnchorElement>,
    workspace: WorkspaceWindowKey,
  ) {
    if (isModifiedClick(event)) {
      closeMobile();
      return;
    }
    event.preventDefault();
    window.dispatchEvent(
      new CustomEvent(OPEN_WORKSPACE_WINDOW_EVENT, { detail: { window: workspace } }),
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
    setBusyConversationId(conversation.id);
    try {
      await apiRequest<Conversation>(`/api/conversations/${conversation.id}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      });
      setConversations((current) =>
        current.map((item) => (item.id === conversation.id ? { ...item, title } : item)),
      );
      setRenamingId(null);
    } catch (caught) {
      setConversationError(
        caught instanceof Error ? caught.message : "Could not rename the conversation.",
      );
    } finally {
      setBusyConversationId(null);
    }
  }

  async function deleteConversation(conversation: ConversationSummary) {
    if (!window.confirm(`Delete “${conversation.title}”?`)) return;
    setBusyConversationId(conversation.id);
    try {
      await apiRequest(`/api/conversations/${conversation.id}`, { method: "DELETE" });
      setConversations((current) => current.filter((item) => item.id !== conversation.id));
      if (activeConversationId === conversation.id) router.push("/?new=1");
    } catch (caught) {
      setConversationError(
        caught instanceof Error ? caught.message : "Could not delete the conversation.",
      );
    } finally {
      setBusyConversationId(null);
    }
  }

  async function importConversation(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    if (file.size > 10_000_000) {
      setConversationError("Conversation exports must be smaller than 10 MB.");
      return;
    }

    setImporting(true);
    setConversationError(null);
    try {
      const transfer = parseConversationTransfer(await file.text());
      const imported = await apiRequest<Conversation>("/api/conversations/import", {
        method: "POST",
        body: JSON.stringify(transfer),
      });
      await refreshConversations();
      router.push(`/?conversation=${encodeURIComponent(imported.id)}`);
      closeMobile();
    } catch (caught) {
      setConversationError(
        caught instanceof Error ? caught.message : "Could not import the conversation.",
      );
    } finally {
      setImporting(false);
    }
  }

  function handleRenameKeyDown(
    event: ReactKeyboardEvent<HTMLInputElement>,
    conversation: ConversationSummary,
  ) {
    if (event.key === "Escape") {
      event.preventDefault();
      setRenamingId(null);
    }
    if (event.key === "Enter") {
      event.preventDefault();
      void saveRename(conversation);
    }
  }

  if (hiddenRoute) return null;

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
          <Link aria-label="Open chat" className="unified-sidebar-brand" href="/" onClick={closeMobile}>
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
            aria-current={activeKey === "chat" && startingNewConversation ? "page" : undefined}
            className="unified-sidebar-row"
            href="/?new=1"
            onClick={closeMobile}
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
                activeKey === "chat" ? "is-active" : ""
              }`}
              onClick={toggleChats}
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
            {!collapsed ? (
              <button
                aria-label="Import conversation"
                className="unified-sidebar-context-action"
                disabled={importing}
                onClick={() => importRef.current?.click()}
                title="Import conversation"
                type="button"
              >
                <Icon name="upload" size={13} />
              </button>
            ) : null}
            <input
              accept=".json,application/json"
              className="unified-sidebar-hidden-input"
              onChange={(event) => void importConversation(event)}
              ref={importRef}
              type="file"
            />
          </div>

          {chatsOpen && !collapsed ? (
            <div
              aria-label="Conversations"
              className="unified-sidebar-conversations"
              id="application-sidebar-conversations"
            >
              {conversationError ? (
                <p className="unified-sidebar-status is-error">{conversationError}</p>
              ) : loadingConversations ? (
                <p className="unified-sidebar-status">Loading conversations…</p>
              ) : visibleConversations.length === 0 ? (
                <p className="unified-sidebar-status">Your conversations will appear here.</p>
              ) : (
                visibleConversations.map((conversation) => {
                  const isActive = activeConversationId === conversation.id;
                  const isBusy = busyConversationId === conversation.id;
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
                          onClick={closeMobile}
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

              {remainingConversationCount > 0 ? (
                <button
                  className="unified-sidebar-show-more"
                  onClick={() =>
                    setConversationLimit((current) => current + CONVERSATION_LIMIT_STEP)
                  }
                  type="button"
                >
                  Show {Math.min(CONVERSATION_LIMIT_STEP, remainingConversationCount)} more
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

        <nav aria-label="Workspaces" className="unified-sidebar-workspaces">
          {workspaceItems.map((item) => (
            <Link
              aria-current={item.active ? "page" : undefined}
              className={`unified-sidebar-row ${item.active ? "is-active" : ""}`}
              href={item.href}
              key={item.key}
              onClick={(event) => openWorkspace(event, item.key)}
              title={item.label}
            >
              <Icon name={item.icon} size={15} />
              <span className="sidebar-label">{item.label}</span>
            </Link>
          ))}
        </nav>

        <footer className="unified-sidebar-footer">
          <button
            aria-label="Open account settings"
            className={`unified-sidebar-owner ${activeKey === "settings" ? "is-active" : ""}`}
            onClick={() => openSettings("account")}
            title={username}
            type="button"
          >
            <span className="unified-sidebar-avatar">{ownerInitial(username)}</span>
            <span className="sidebar-label">{username}</span>
          </button>
          <button
            aria-label="Open settings"
            className="unified-sidebar-icon-button unified-sidebar-settings-button"
            onClick={() => openSettings()}
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
