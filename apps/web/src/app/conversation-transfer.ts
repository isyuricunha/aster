import type {
  ChatMessage,
  Conversation,
  ConversationPersona,
  ConversationTransfer,
  ConversationTransferMessage,
  ToolCall,
} from "../lib/api";

export function createConversationTransfer(conversation: Conversation): ConversationTransfer {
  return {
    format: "aster-conversation",
    version: 3,
    title: conversation.title,
    persona: conversation.persona,
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

  if (conversation.persona) {
    lines.push(
      `> Persona: ${conversation.persona.name}`,
      `> Instruction role: ${conversation.persona.instruction_role}`,
      "",
    );
  } else {
    lines.push("> Persona: none", "");
  }

  for (const message of conversation.messages) {
    lines.push(`## ${messageHeading(message)}`, "");
    const metadata = messageMetadata(message);
    if (metadata) lines.push(`_${metadata}_`, "");
    if (message.tool_calls?.length) {
      for (const call of message.tool_calls) {
        lines.push(
          `### Tool request: ${call.function.name}`,
          "",
          "```json",
          formatJson(call.function.arguments),
          "```",
          "",
        );
      }
    }
    lines.push(message.content || "_(empty message)_", "");
    if (message.error_message) lines.push(`> Error: ${message.error_message}`, "");
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

export function parseConversationTransfer(raw: string): ConversationTransfer {
  const value = JSON.parse(raw) as unknown;
  if (!isRecord(value)) throw new Error("The selected file does not contain a JSON object.");
  if (
    value.format !== "aster-conversation" ||
    (value.version !== 1 && value.version !== 2 && value.version !== 3)
  ) {
    throw new Error("This is not a supported Aster conversation export.");
  }
  if (typeof value.title !== "string" || !value.title.trim()) {
    throw new Error("The exported conversation does not contain a valid title.");
  }
  if (!Array.isArray(value.messages)) {
    throw new Error("The exported conversation does not contain a message list.");
  }
  if (
    value.version >= 2 &&
    value.persona !== null &&
    value.persona !== undefined &&
    !isConversationPersona(value.persona)
  ) {
    throw new Error("The exported conversation contains an invalid persona snapshot.");
  }
  if (value.version === 1 && "persona" in value) {
    throw new Error("Version 1 conversation exports cannot contain a persona snapshot.");
  }

  for (const message of value.messages) {
    if (!isTransferMessage(message, value.version)) {
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
    tool_calls: message.tool_calls ?? null,
    tool_call_id: message.tool_call_id ?? null,
    tool_name: message.tool_name ?? null,
  };
}

function messageHeading(message: ChatMessage): string {
  if (message.role === "user") return "You";
  if (message.role === "tool") return `Tool · ${message.tool_name ?? "unknown"}`;
  return "Aster";
}

function messageMetadata(message: ChatMessage): string {
  const metadata: string[] = [];
  if (message.status !== "completed") metadata.push(`Status: ${message.status}`);
  if (message.model_id) metadata.push(`Model: ${message.model_id}`);
  if (message.tool_call_id) metadata.push(`Call: ${message.tool_call_id}`);
  return metadata.join(" · ");
}

function formatJson(value: string): string {
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
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

function isConversationPersona(value: unknown): value is ConversationPersona {
  if (!isRecord(value)) return false;
  const validSource =
    value.source_persona_id === null || typeof value.source_persona_id === "string";
  const validRole = value.instruction_role === "developer" || value.instruction_role === "system";
  return (
    validSource &&
    validRole &&
    typeof value.name === "string" &&
    value.name.trim().length > 0 &&
    typeof value.description === "string" &&
    typeof value.instructions === "string"
  );
}

function isTransferMessage(value: unknown, version: 1 | 2 | 3): value is ConversationTransferMessage {
  if (!isRecord(value)) return false;
  const validRole =
    value.role === "user" || value.role === "assistant" || (version === 3 && value.role === "tool");
  const validStatus =
    value.status === "completed" || value.status === "failed" || value.status === "stopped";
  const validError = value.error_message === null || typeof value.error_message === "string";
  const validModel = value.model_id === null || typeof value.model_id === "string";
  if (!validRole || !validStatus || typeof value.content !== "string" || !validError || !validModel) {
    return false;
  }

  const toolCalls = value.tool_calls;
  const validCalls = toolCalls === undefined || toolCalls === null || isToolCallList(toolCalls);
  const validCallId =
    value.tool_call_id === undefined ||
    value.tool_call_id === null ||
    typeof value.tool_call_id === "string";
  const validToolName =
    value.tool_name === undefined || value.tool_name === null || typeof value.tool_name === "string";
  if (!validCalls || !validCallId || !validToolName) return false;
  if (version < 3 && (toolCalls || value.tool_call_id || value.tool_name || value.role === "tool")) {
    return false;
  }
  if (value.role === "tool") {
    return typeof value.tool_call_id === "string" && typeof value.tool_name === "string";
  }
  return true;
}

function isToolCallList(value: unknown): value is ToolCall[] {
  return Array.isArray(value) && value.every(isToolCall);
}

function isToolCall(value: unknown): value is ToolCall {
  if (!isRecord(value) || value.type !== "function" || typeof value.id !== "string") return false;
  const fn = value.function;
  return (
    isRecord(fn) &&
    typeof fn.name === "string" &&
    typeof fn.arguments === "string"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
