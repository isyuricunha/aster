import type { Metadata } from "next";

import type { Conversation, ConversationSummary, ModelPreferences } from "../lib/api";
import { requireServerAuth, serverApiFetch } from "../lib/server-api";
import { ChatShell } from "./chat-shell";

export const metadata: Metadata = { title: { absolute: "Chat · Aster" } };

export const dynamic = "force-dynamic";

type InitialChatData = {
  conversations: ConversationSummary[];
  activeConversation: Conversation | null;
  preferences: ModelPreferences | null;
  error: string | null;
};

async function getInitialChatData(
  preferredConversationId?: string,
  startNewConversation = false,
): Promise<InitialChatData> {
  try {
    const [conversationResponse, preferenceResponse] = await Promise.all([
      serverApiFetch("/api/conversations"),
      serverApiFetch("/api/model-preferences"),
    ]);
    if (!conversationResponse.ok || !preferenceResponse.ok) {
      throw new Error("The chat API returned an error.");
    }

    const conversations = (await conversationResponse.json()) as ConversationSummary[];
    const preferences = (await preferenceResponse.json()) as ModelPreferences;
    let activeConversation: Conversation | null = null;
    const preferred = conversations.find((item) => item.id === preferredConversationId);
    const activeSummary = startNewConversation ? undefined : (preferred ?? conversations[0]);

    if (activeSummary) {
      const activeResponse = await serverApiFetch(`/api/conversations/${activeSummary.id}`);
      if (activeResponse.ok) {
        activeConversation = (await activeResponse.json()) as Conversation;
      }
    }

    return { conversations, activeConversation, preferences, error: null };
  } catch (caught) {
    return {
      conversations: [],
      activeConversation: null,
      preferences: null,
      error: caught instanceof Error ? caught.message : "Could not load the chat.",
    };
  }
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{
    conversation?: string | string[];
    new?: string | string[];
  }>;
}) {
  await requireServerAuth();
  const params = await searchParams;
  const preferredConversationId =
    typeof params.conversation === "string" ? params.conversation : undefined;
  const startNewConversation = params.new === "1";
  const initialData = await getInitialChatData(preferredConversationId, startNewConversation);
  const chatKey = startNewConversation ? "new" : (initialData.activeConversation?.id ?? "empty");
  return <ChatShell key={chatKey} {...initialData} />;
}
