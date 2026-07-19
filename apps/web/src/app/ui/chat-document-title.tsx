"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";

import {
  apiRequest,
  type ConversationSummary,
  type PersonaPreferences,
} from "../../lib/api";

const CONVERSATIONS_CHANGED_EVENT = "aster:conversations-changed";
const FALLBACK_ASSISTANT_NAME = "Aster";
const NEW_CHAT_TITLE = "New chat";
const ASSISTANT_LABEL_SELECTOR = ".chat-message.assistant .message-label > span";

type ConversationChangeEvent = CustomEvent<{
  conversationId?: string;
}>;

function normalizedText(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function renderedConversationTitle(): string | null {
  const title = document.querySelector<HTMLElement>(".chat-header .chat-title")?.textContent;
  const normalized = normalizedText(title);
  return normalized === "New conversation" ? NEW_CHAT_TITLE : normalized;
}

function applyAssistantName(name: string): void {
  document.querySelectorAll<HTMLElement>(ASSISTANT_LABEL_SELECTOR).forEach((label) => {
    if (label.textContent !== name) label.textContent = name;
    label.setAttribute("aria-label", name);
  });
}

export function ChatDocumentTitle() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const routeSearch = searchParams.toString();
  const requestIdRef = useRef(0);
  const assistantNameRef = useRef(FALLBACK_ASSISTANT_NAME);

  const updateIdentity = useCallback(
    async (conversationId: string | null, startNewConversation: boolean) => {
      const requestId = ++requestIdRef.current;

      try {
        const [conversations, preferences] = await Promise.all([
          apiRequest<ConversationSummary[]>("/api/conversations"),
          apiRequest<PersonaPreferences>("/api/persona-preferences"),
        ]);
        if (requestId !== requestIdRef.current) return;

        const activeConversation = startNewConversation
          ? undefined
          : conversationId
            ? conversations.find((conversation) => conversation.id === conversationId)
            : conversations[0];
        const assistantName =
          normalizedText(activeConversation?.persona_name) ??
          normalizedText(preferences.default_persona?.name) ??
          FALLBACK_ASSISTANT_NAME;

        assistantNameRef.current = assistantName;
        applyAssistantName(assistantName);

        if (pathname === "/") {
          document.title = activeConversation?.title?.trim() || NEW_CHAT_TITLE;
        }
      } catch {
        assistantNameRef.current = FALLBACK_ASSISTANT_NAME;
        applyAssistantName(FALLBACK_ASSISTANT_NAME);
        if (pathname === "/") {
          document.title = renderedConversationTitle() ?? NEW_CHAT_TITLE;
        }
      }
    },
    [pathname],
  );

  useEffect(() => {
    requestIdRef.current += 1;
    if (pathname !== "/") return;

    function syncIdentity(conversationId?: string) {
      const url = new URL(window.location.href);
      const eventConversationId = conversationId ?? url.searchParams.get("conversation");
      const startNewConversation = url.searchParams.get("new") === "1" && !conversationId;
      void updateIdentity(eventConversationId, startNewConversation);
    }

    function handleConversationChange(event: Event) {
      const detail = (event as ConversationChangeEvent).detail;
      syncIdentity(detail?.conversationId);
    }

    const observer = new MutationObserver(() => {
      applyAssistantName(assistantNameRef.current);
      const title = renderedConversationTitle();
      if (title) document.title = title;
    });

    observer.observe(document.body, {
      childList: true,
      characterData: true,
      subtree: true,
    });
    syncIdentity();
    window.addEventListener(CONVERSATIONS_CHANGED_EVENT, handleConversationChange);

    return () => {
      requestIdRef.current += 1;
      observer.disconnect();
      window.removeEventListener(CONVERSATIONS_CHANGED_EVENT, handleConversationChange);
    };
  }, [pathname, routeSearch, updateIdentity]);

  return null;
}
