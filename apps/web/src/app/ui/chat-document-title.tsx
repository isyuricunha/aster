"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef } from "react";

import {
  apiRequest,
  type ConversationSummary,
  type PersonaPreferences,
} from "../../lib/api";

const CONVERSATIONS_CHANGED_EVENT = "aster:conversations-changed";
const FALLBACK_PERSONA_NAME = "Aster";

type ConversationChangeEvent = CustomEvent<{
  conversationId?: string;
}>;

function normalizedPersonaName(name: string | null | undefined): string | null {
  const normalized = name?.trim();
  return normalized ? normalized : null;
}

export function ChatDocumentTitle() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const routeSearch = searchParams.toString();
  const requestIdRef = useRef(0);

  const updateTitle = useCallback(
    async (conversationId: string | null, startNewConversation: boolean) => {
      const requestId = ++requestIdRef.current;

      try {
        let resolvedConversation = false;
        let personaName: string | null = null;

        if (!startNewConversation) {
          const conversations = await apiRequest<ConversationSummary[]>("/api/conversations");
          if (requestId !== requestIdRef.current) return;

          const activeConversation = conversationId
            ? conversations.find((conversation) => conversation.id === conversationId)
            : conversations[0];
          if (activeConversation) {
            resolvedConversation = true;
            personaName = normalizedPersonaName(activeConversation.persona_name);
          }
        }

        if (!resolvedConversation) {
          const preferences = await apiRequest<PersonaPreferences>("/api/persona-preferences");
          if (requestId !== requestIdRef.current) return;
          personaName = normalizedPersonaName(preferences.default_persona?.name);
        }

        if (pathname === "/" && requestId === requestIdRef.current) {
          document.title = `Chat · ${personaName ?? FALLBACK_PERSONA_NAME}`;
        }
      } catch {
        if (pathname === "/" && requestId === requestIdRef.current) {
          document.title = `Chat · ${FALLBACK_PERSONA_NAME}`;
        }
      }
    },
    [pathname],
  );

  useEffect(() => {
    requestIdRef.current += 1;
    if (pathname !== "/") return;

    function syncTitle(conversationId?: string) {
      const url = new URL(window.location.href);
      const eventConversationId = conversationId ?? url.searchParams.get("conversation");
      const startNewConversation = url.searchParams.get("new") === "1" && !conversationId;
      void updateTitle(eventConversationId, startNewConversation);
    }

    function handleConversationChange(event: Event) {
      const detail = (event as ConversationChangeEvent).detail;
      syncTitle(detail?.conversationId);
    }

    syncTitle();
    window.addEventListener(CONVERSATIONS_CHANGED_EVENT, handleConversationChange);
    return () => {
      requestIdRef.current += 1;
      window.removeEventListener(CONVERSATIONS_CHANGED_EVENT, handleConversationChange);
    };
  }, [pathname, routeSearch, updateTitle]);

  return null;
}
