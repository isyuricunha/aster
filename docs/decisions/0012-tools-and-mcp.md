# ADR-0012: Tool calling and MCP execution

## Status

Accepted for Stage 12.

## Context

Aster could stream model responses but could not let a model request external capabilities. Adding tool execution introduces a trust boundary: the model may propose an action, but the application owns discovery, permissions, confirmation, execution, persistence, and error handling.

MCP provides a provider-neutral protocol for discovering and invoking tools. OpenAI-compatible chat completions provide a common tool-call shape for models. Neither protocol decides which tools the owner trusts or which conversation may use them.

## Decision

Aster stores MCP servers and their discovered tools separately.

Streamable HTTP is the default transport. Stdio is available only when `ASTER_MCP_STDIO_ENABLED=true`; commands are executed directly without a shell. HTTP headers and stdio environment values are encrypted with the existing Aster encryption key. API responses expose only secret names.

Discovered tools start disabled, are not assigned to new conversations, and require confirmation. The owner may change three independent policies:

- whether the tool is enabled globally;
- whether new conversations receive it by default;
- whether each call requires confirmation.

Each conversation stores an explicit set of available tools. Changing a global default does not retroactively modify existing conversations.

Aster sends only enabled, available, conversation-scoped tools to the model. Public tool names are stable and namespaced so equal MCP tool names from different servers cannot collide.

Assistant tool calls, tool-role messages, and execution records are persisted. An execution records arguments, status, result or error, approval state, and timestamps. Tool results are inserted into model context as untrusted data.

Aster pauses the model loop when confirmation is required. Approving or denying the call appends the corresponding tool result and resumes the same conversation history. New messages, persona changes, edit/resend, regeneration, and tool-scope changes are blocked while approval is pending.

Tool loops are bounded by configured round, argument, result, and timeout limits. Model fallback remains allowed only before any content or tool-call delta is emitted.

Conversation transfer version 3 preserves assistant tool calls and tool-role results. It does not export MCP credentials, server configuration, local execution IDs, or approval audit records.

## Consequences

- Models can use tools without receiving credentials or direct network access.
- The owner remains the final authority for sensitive calls.
- Tool behavior is reproducible in chat history and visible after restart.
- A missing, disabled, denied, or failed tool remains explicit to the model and user.
- Stdio is intentionally opt-in because it starts local processes inside the API container.
- Tool execution is synchronous and bounded in Stage 12; background jobs and automations remain later work.
- MCP resources, prompts, sampling, elicitation, OAuth flows, and server-initiated features are outside Stage 12.
