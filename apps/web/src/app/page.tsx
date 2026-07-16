import type { Conversation, ConversationSummary, ModelPreferences } from "../lib/api";
import { requireServerAuth, serverApiFetch } from "../lib/server-api";
import { ChatShell } from "./chat-shell";

export const dynamic = "force-dynamic";

type InitialChatData = {
  conversations: ConversationSummary[];
  activeConversation: Conversation | null;
  preferences: ModelPreferences | null;
  error: string | null;
};

async function getInitialChatData(): Promise<InitialChatData> {
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

    if (conversations[0]) {
      const activeResponse = await serverApiFetch(
        `/api/conversations/${conversations[0].id}`,
      );
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
  await requireServerAuth();
  const initialData = await getInitialChatData();
  return <ChatShell {...initialData} />;
}
