import type {
  ChatMessage,
  Conversation,
  ConversationTransfer,
  ConversationTransferMessage,
} from "../lib/api";

export function createConversationTransfer(conversation: Conversation): ConversationTransfer {
  return {
    format: "aster-conversation",
    version: 1,
    title: conversation.title,
    messages: conversation.messages.map(toTransferMessage),
  };
}

export function createConversationMarkdown(conversation: Conversation): string {
  const lines = [
    `# ${conversation.title}`,
    "",
    `> Exported from Aster on ${new Date().toISOString()}`,
    "",
  ];

  for (const message of conversation.messages) {
    lines.push(`## ${message.role === "user" ? "You" : "Aster"}`, "");
    const metadata = messageMetadata(message);
    if (metadata) lines.push(`_${metadata}_`, "");
    lines.push(message.content || "_(empty message)_", "");
    if (message.error_message) lines.push(`> Error: ${message.error_message}`, "");
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

export function parseConversationTransfer(raw: string): ConversationTransfer {
  const value = JSON.parse(raw) as unknown;
  if (!isRecord(value)) throw new Error("The selected file does not contain a JSON object.");
  if (value.format !== "aster-conversation" || value.version !== 1) {
    throw new Error("This is not a supported Aster conversation export.");
  }
  if (typeof value.title !== "string" || !value.title.trim()) {
    throw new Error("The exported conversation does not contain a valid title.");
  }
  if (!Array.isArray(value.messages)) {
    throw new Error("The exported conversation does not contain a message list.");
  }

  for (const message of value.messages) {
    if (!isTransferMessage(message)) {
      throw new Error("The exported conversation contains an invalid message.");
    }
  }

  return value as ConversationTransfer;
}

export function downloadConversationFile(
  content: string,
  conversationTitle: string,
  extension: "aster.json" | "md",
  type: string,
): void {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${safeFileName(conversationTitle)}.${extension}`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function toTransferMessage(message: ChatMessage): ConversationTransferMessage {
  if (message.status === "streaming") {
    throw new Error("A conversation cannot be exported while a response is streaming.");
  }
  return {
    role: message.role,
    content: message.content,
    status: message.status,
    error_message: message.error_message,
    model_id: message.model_id,
  };
}

function messageMetadata(message: ChatMessage): string {
  const metadata: string[] = [];
  if (message.status !== "completed") metadata.push(`Status: ${message.status}`);
  if (message.model_id) metadata.push(`Model: ${message.model_id}`);
  return metadata.join(" · ");
}

function safeFileName(value: string): string {
  const normalized = value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return normalized || "aster-conversation";
}

function isTransferMessage(value: unknown): value is ConversationTransferMessage {
  if (!isRecord(value)) return false;
  const validRole = value.role === "user" || value.role === "assistant";
  const validStatus =
    value.status === "completed" || value.status === "failed" || value.status === "stopped";
  const validError = value.error_message === null || typeof value.error_message === "string";
  const validModel = value.model_id === null || typeof value.model_id === "string";
  return validRole && validStatus && typeof value.content === "string" && validError && validModel;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
