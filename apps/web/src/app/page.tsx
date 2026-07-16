import type { Conversation, ConversationSummary, ModelPreferences } from "../lib/api";
import { ChatShell } from "./chat-shell";

export const dynamic = "force-dynamic";

type InitialChatData = {
  conversations: ConversationSummary[];
  activeConversation: Conversation | null;
  preferences: ModelPreferences | null;
  error: string | null;
};

async function getInitialChatData(): Promise<InitialChatData> {
  const baseUrl = process.env.ASTER_API_INTERNAL_URL ?? "http://localhost:8000";

  try {
    const [conversationResponse, preferenceResponse] = await Promise.all([
      fetch(`${baseUrl}/api/conversations`, { cache: "no-store" }),
      fetch(`${baseUrl}/api/model-preferences`, { cache: "no-store" }),
    ]);
    if (!conversationResponse.ok || !preferenceResponse.ok) {
      throw new Error("The chat API returned an error.");
    }

    const conversations = (await conversationResponse.json()) as ConversationSummary[];
    const preferences = (await preferenceResponse.json()) as ModelPreferences;
    let activeConversation: Conversation | null = null;

    if (conversations[0]) {
      const activeResponse = await fetch(`${baseUrl}/api/conversations/${conversations[0].id}`, {
        cache: "no-store",
      });
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

export default async function Home() {
  const initialData = await getInitialChatData();
  return <ChatShell {...initialData} />;
}
