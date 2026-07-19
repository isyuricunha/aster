"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";

import { apiRequest, type ConversationSummary } from "../../lib/api";
import { Icon, type IconName } from "./icons";
import {
  OPEN_SETTINGS_EVENT,
  OPEN_WORKSPACE_WINDOW_EVENT,
  type SettingsSection,
  type WorkspaceWindowKey,
} from "./workspace-window-host";

export const OPEN_COMMAND_PALETTE_EVENT = "aster:open-command-palette";

type PaletteAction =
  | { type: "route"; href: string }
  | { type: "workspace"; window: WorkspaceWindowKey }
  | { type: "settings"; section: SettingsSection }
  | { type: "conversation"; conversationId: string };

type PaletteItem = {
  id: string;
  group: "Actions" | "Workspace" | "Settings" | "Conversations";
  label: string;
  description: string;
  icon: IconName;
  keywords: string;
  action: PaletteAction;
  meta?: string;
};

type PaletteGroup = {
  label: PaletteItem["group"];
  items: PaletteItem[];
};

const STATIC_ITEMS: readonly PaletteItem[] = [
  {
    id: "action:new-chat",
    group: "Actions",
    label: "New chat",
    description: "Start a blank conversation",
    icon: "new-chat",
    keywords: "new conversation compose blank start",
    action: { type: "route", href: "/?new=1" },
    meta: "N",
  },
  {
    id: "workspace:chat",
    group: "Workspace",
    label: "Chat",
    description: "Open the primary conversation workspace",
    icon: "chat",
    keywords: "home conversations assistant",
    action: { type: "route", href: "/" },
  },
  {
    id: "workspace:communications",
    group: "Workspace",
    label: "Communications",
    description: "Open email, Discord, accounts, and rules",
    icon: "chat",
    keywords: "email inbox discord messages channels",
    action: { type: "workspace", window: "communications" },
  },
  {
    id: "workspace:agents",
    group: "Workspace",
    label: "Agents",
    description: "Open goals, runs, approvals, and controls",
    icon: "tools",
    keywords: "autonomous goals runs approvals tasks",
    action: { type: "workspace", window: "agents" },
  },
  {
    id: "workspace:images",
    group: "Workspace",
    label: "Images",
    description: "Open the private gallery and image capabilities",
    icon: "images",
    keywords: "gallery generation editing visual media",
    action: { type: "workspace", window: "images" },
  },
  {
    id: "workspace:automations",
    group: "Workspace",
    label: "Automations",
    description: "Open schedules, runs, integrations, and notifications",
    icon: "refresh",
    keywords: "scheduled jobs workflows integrations notifications",
    action: { type: "workspace", window: "automations" },
  },
  {
    id: "settings:models",
    group: "Settings",
    label: "Models",
    description: "Endpoints, roles, profiles, and fallbacks",
    icon: "models",
    keywords: "providers endpoints primary utility image embedding routing",
    action: { type: "settings", section: "models" },
  },
  {
    id: "settings:persona",
    group: "Settings",
    label: "Personas",
    description: "Reusable identities and conversation defaults",
    icon: "persona",
    keywords: "persona identity instructions behavior",
    action: { type: "settings", section: "persona" },
  },
  {
    id: "settings:memory",
    group: "Settings",
    label: "Memory & Knowledge",
    description: "Approved memory, documents, and retrieval",
    icon: "memory",
    keywords: "rag documents collections embeddings recall",
    action: { type: "settings", section: "memory" },
  },
  {
    id: "settings:tools",
    group: "Settings",
    label: "Tools",
    description: "MCP servers, scopes, and confirmations",
    icon: "tools",
    keywords: "mcp tools permissions confirmations servers",
    action: { type: "settings", section: "tools" },
  },
  {
    id: "settings:account",
    group: "Settings",
    label: "Account",
    description: "Owner password and active sessions",
    icon: "account",
    keywords: "security password sessions owner",
    action: { type: "settings", section: "account" },
  },
];

const GROUP_ORDER: readonly PaletteItem["group"][] = [
  "Actions",
  "Workspace",
  "Settings",
  "Conversations",
];

function isPublicRoute(pathname: string): boolean {
  return ["/login", "/setup", "/signin", "/sign-in", "/auth"].some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function normalize(value: string): string {
  return value.trim().toLocaleLowerCase();
}

function itemDomId(item: PaletteItem): string {
  return `command-palette-item-${item.id.replaceAll(/[^a-zA-Z0-9_-]/g, "-")}`;
}

function conversationMeta(conversation: ConversationSummary): string {
  const messageLabel = `${conversation.message_count} message${conversation.message_count === 1 ? "" : "s"}`;
  return conversation.persona_name ? `${messageLabel} · ${conversation.persona_name}` : messageLabel;
}

function conversationItem(conversation: ConversationSummary): PaletteItem {
  return {
    id: `conversation:${conversation.id}`,
    group: "Conversations",
    label: conversation.title,
    description: conversationMeta(conversation),
    icon: "chat",
    keywords: `${conversation.title} ${conversation.persona_name ?? ""}`,
    action: { type: "conversation", conversationId: conversation.id },
  };
}

export function CommandPaletteHost() {
  const pathname = usePathname();
  const router = useRouter();
  const available = !isPublicRoute(pathname);
  const inputRef = useRef<HTMLInputElement>(null);
  const lastFocusedRef = useRef<HTMLElement | null>(null);
  const requestRef = useRef(0);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [conversationError, setConversationError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const normalizedQuery = normalize(query);
  const groups = useMemo<PaletteGroup[]>(() => {
    const staticItems = STATIC_ITEMS.filter((item) => {
      if (!normalizedQuery) return true;
      return normalize(`${item.label} ${item.description} ${item.keywords}`).includes(normalizedQuery);
    });
    const conversationItems = conversations.slice(0, 12).map(conversationItem);
    const allItems = [...staticItems, ...conversationItems];

    return GROUP_ORDER.map((label) => ({
      label,
      items: allItems.filter((item) => item.group === label),
    })).filter((group) => group.items.length > 0);
  }, [conversations, normalizedQuery]);
  const flatItems = useMemo(() => groups.flatMap((group) => group.items), [groups]);
  const selectedItem = flatItems[selectedIndex] ?? null;

  function closePalette(restoreFocus = true) {
    requestRef.current += 1;
    setOpen(false);
    setQuery("");
    setConversationError(null);
    setLoadingConversations(false);
    setSelectedIndex(0);
    if (restoreFocus) {
      requestAnimationFrame(() => lastFocusedRef.current?.focus());
    }
  }

  function openPalette() {
    if (!available) return;
    lastFocusedRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setOpen(true);
    setQuery("");
    setConversationError(null);
    setSelectedIndex(0);
  }

  useEffect(() => {
    const handleOpen = () => openPalette();
    const handleKeyDown = (event: KeyboardEvent) => {
      const shortcut =
        (event.ctrlKey || event.metaKey) &&
        !event.altKey &&
        event.key.toLocaleLowerCase() === "k";

      if (shortcut && available) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        if (open) closePalette();
        else openPalette();
        return;
      }

      if (open && event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        closePalette();
      }
    };

    window.addEventListener(OPEN_COMMAND_PALETTE_EVENT, handleOpen);
    window.addEventListener("keydown", handleKeyDown, true);
    return () => {
      window.removeEventListener(OPEN_COMMAND_PALETTE_EVENT, handleOpen);
      window.removeEventListener("keydown", handleKeyDown, true);
    };
  }, [available, open]);

  useEffect(() => {
    if (!open) return;
    document.body.classList.add("command-palette-open");
    requestAnimationFrame(() => inputRef.current?.focus());
    return () => document.body.classList.remove("command-palette-open");
  }, [open]);

  useEffect(() => {
    if (open && !available) closePalette(false);
  }, [available, open]);

  useEffect(() => {
    if (!open) return;
    const requestId = ++requestRef.current;
    const search = query.trim();
    setLoadingConversations(true);
    setConversationError(null);

    const timer = window.setTimeout(
      () => {
        const path = search
          ? `/api/conversations?query=${encodeURIComponent(search)}`
          : "/api/conversations";
        void apiRequest<ConversationSummary[]>(path)
          .then((results) => {
            if (requestRef.current === requestId) setConversations(results);
          })
          .catch((caught: unknown) => {
            if (requestRef.current !== requestId) return;
            setConversationError(
              caught instanceof Error ? caught.message : "Could not search conversations.",
            );
            setConversations([]);
          })
          .finally(() => {
            if (requestRef.current === requestId) setLoadingConversations(false);
          });
      },
      search ? 180 : 0,
    );

    return () => window.clearTimeout(timer);
  }, [open, query]);

  useEffect(() => setSelectedIndex(0), [query]);

  useEffect(() => {
    setSelectedIndex((current) => Math.min(current, Math.max(flatItems.length - 1, 0)));
  }, [flatItems.length]);

  useEffect(() => {
    if (!open || !selectedItem) return;
    document.getElementById(itemDomId(selectedItem))?.scrollIntoView({ block: "nearest" });
  }, [open, selectedItem]);

  function execute(item: PaletteItem) {
    closePalette(false);
    requestAnimationFrame(() => {
      if (item.action.type === "route") {
        router.push(item.action.href);
        return;
      }
      if (item.action.type === "conversation") {
        router.push(`/?conversation=${encodeURIComponent(item.action.conversationId)}`);
        return;
      }
      if (item.action.type === "workspace") {
        window.dispatchEvent(
          new CustomEvent(OPEN_WORKSPACE_WINDOW_EVENT, {
            detail: { window: item.action.window },
          }),
        );
        return;
      }
      window.dispatchEvent(
        new CustomEvent(OPEN_SETTINGS_EVENT, {
          detail: { section: item.action.section },
        }),
      );
    });
  }

  function handleInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (flatItems.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelectedIndex((current) => (current + 1) % flatItems.length);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelectedIndex((current) => (current - 1 + flatItems.length) % flatItems.length);
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      setSelectedIndex(0);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      setSelectedIndex(flatItems.length - 1);
      return;
    }
    if (event.key === "Enter" && selectedItem) {
      event.preventDefault();
      execute(selectedItem);
    }
  }

  function handleBackdropMouseDown(event: ReactMouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) closePalette();
  }

  if (!open || !available) return null;

  return (
    <div className="command-palette-layer" onMouseDown={handleBackdropMouseDown}>
      <section
        aria-label="Command palette"
        aria-modal="true"
        className="command-palette"
        role="dialog"
      >
        <div className="command-palette-search">
          <Icon name="search" size={18} />
          <input
            aria-activedescendant={selectedItem ? itemDomId(selectedItem) : undefined}
            aria-autocomplete="list"
            aria-controls="command-palette-results"
            aria-expanded="true"
            aria-label="Search commands and conversations"
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="Search commands or conversations…"
            ref={inputRef}
            role="combobox"
            type="text"
            value={query}
          />
          <kbd>Esc</kbd>
        </div>

        <div className="command-palette-results" id="command-palette-results" role="listbox">
          {groups.map((group) => (
            <section aria-label={group.label} className="command-palette-group" key={group.label}>
              <h2>{group.label}</h2>
              <div>
                {group.items.map((item) => {
                  const index = flatItems.findIndex((candidate) => candidate.id === item.id);
                  const selected = index === selectedIndex;
                  return (
                    <button
                      aria-selected={selected}
                      className={selected ? "selected" : ""}
                      id={itemDomId(item)}
                      key={item.id}
                      onClick={() => execute(item)}
                      onMouseMove={() => setSelectedIndex(index)}
                      role="option"
                      type="button"
                    >
                      <span className="command-palette-icon">
                        <Icon name={item.icon} size={16} />
                      </span>
                      <span className="command-palette-copy">
                        <strong>{item.label}</strong>
                        <small>{item.description}</small>
                      </span>
                      {item.meta ? <kbd>{item.meta}</kbd> : <Icon name="chevron-right" size={14} />}
                    </button>
                  );
                })}
              </div>
            </section>
          ))}

          {loadingConversations ? (
            <div aria-live="polite" className="command-palette-status">
              Searching conversations…
            </div>
          ) : null}
          {conversationError ? (
            <div aria-live="polite" className="command-palette-status command-palette-error">
              {conversationError}
            </div>
          ) : null}
          {!loadingConversations && !conversationError && flatItems.length === 0 ? (
            <div className="command-palette-empty">
              <Icon name="search" size={24} />
              <strong>No matching commands or conversations</strong>
              <span>Try a workspace name, setting, conversation title, or message text.</span>
            </div>
          ) : null}
        </div>

        <footer className="command-palette-footer">
          <span>
            <kbd>↑</kbd>
            <kbd>↓</kbd>
            Navigate
          </span>
          <span>
            <kbd>Enter</kbd>
            Open
          </span>
          <span>Search includes conversation message history</span>
        </footer>
      </section>
    </div>
  );
}
