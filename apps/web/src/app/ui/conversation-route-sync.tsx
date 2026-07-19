"use client";

import { useEffect } from "react";

import { apiRequest, type ConversationSummary } from "../../lib/api";

const CONVERSATIONS_CHANGED_EVENT = "aster:conversations-changed";

type ConversationChangeEvent = CustomEvent<{
  conversationId?: string;
}>;

function isNewChatUrl(url: URL): boolean {
  return url.pathname === "/" && url.searchParams.get("new") === "1";
}

function replaceNewChatUrl(conversationId: string): void {
  const url = new URL(window.location.href);
  if (!isNewChatUrl(url)) return;

  url.searchParams.delete("new");
  url.searchParams.set("conversation", conversationId);
  window.history.replaceState(
    window.history.state,
    "",
    `${url.pathname}${url.search}${url.hash}`,
  );
}

export function ConversationRouteSync() {
  useEffect(() => {
    let requestId = 0;

    async function handleConversationChange(event: Event) {
      const currentUrl = new URL(window.location.href);
      if (!isNewChatUrl(currentUrl)) return;

      const detail = (event as ConversationChangeEvent).detail;
      if (detail?.conversationId) {
        replaceNewChatUrl(detail.conversationId);
        return;
      }

      const currentRequest = ++requestId;
      try {
        const conversations = await apiRequest<ConversationSummary[]>("/api/conversations");
        if (currentRequest !== requestId) return;

        const createdConversation = conversations.find(
          (conversation) => conversation.title === "New chat" && conversation.message_count === 0,
        );
        if (createdConversation) replaceNewChatUrl(createdConversation.id);
      } catch {
        // Conversation creation remains successful even when route synchronization cannot refresh.
      }
    }

    window.addEventListener(CONVERSATIONS_CHANGED_EVENT, handleConversationChange);
    return () => {
      requestId += 1;
      window.removeEventListener(CONVERSATIONS_CHANGED_EVENT, handleConversationChange);
    };
  }, []);

  return null;
}
