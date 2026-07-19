# Core workspaces

Aster keeps chat as the primary surface and exposes the remaining product areas through the unified sidebar, command palette, floating windows, and normal full-page routes.

## Chat

Chat supports:

- streamed responses and visible generation state;
- reasoning collapsed by default when a provider exposes it;
- edit and resend;
- regenerate and stop;
- safe Markdown, GFM, tables, and highlighted code;
- message and code-block copy actions;
- conversation rename, delete, search, import, and export;
- visible tool calls, retrieval provenance, and image attachments.

A new conversation is persisted as soon as its first message is sent. The URL and active sidebar item then transition to the persisted conversation ID without interrupting the response stream.

## Navigation

The unified sidebar contains:

- New chat;
- global Search;
- expandable conversation history;
- Communications, Agents, Images, and Automations;
- owner identity and Settings in the fixed footer.

`Ctrl K` or `Command K` opens the command palette. It searches actions, workspaces, settings, and conversation history.

On desktop, the sidebar can collapse to an icon rail. On narrow screens it becomes a modal drawer.

## Floating workspaces

Settings, Communications, Agents, Images, and Automations can open as movable and resizable windows over chat.

Each window supports focus ordering, minimize, restore, close, remembered geometry, a minimized dock, and a full-page fallback. Narrow screens use a single full-screen active workspace.

## Models

Models configuration manages endpoints, catalogs, model roles, profiles, fallbacks, and declared capabilities.

The simple surface covers the common workflow. Maintenance and provider-specific controls remain under **Advanced settings**.

## Personas

Personas are reusable assistant identities. A selected persona is frozen into a conversation, automation, or agent run so later edits cannot silently rewrite existing work.

## Memory and knowledge

The workspace separates Memories, Documents, Collections, and Retrieval.

Retrieval sources are persisted with the assistant response. The chat shows a compact source control that expands only when the owner wants to inspect the selected memory or document chunks.

## Tools

Tools manages MCP servers, discovered capabilities, connection status, enablement, default scopes, and confirmation rules.

Interactive chat tools and autonomous-agent tool scopes are explicit and independently auditable.

## Images

Images supports provider-declared generation and editing operations, private input and output storage, operation history, gallery browsing, and conversation association.

Ordinary text chat does not infer image intent from keywords. Image operations are explicit.

## Automations

Automations provides durable one-time, interval, daily, weekly, communication-event, and inbound-webhook work.

Definitions, runs, retries, notifications, and external delivery attempts remain inspectable. Automatic retries stop before uncertain external side effects are repeated.

## Communications

Communications provides private IMAP and Discord inboxes, synchronized threads, attachments, unread state, search, manual replies, AI-assisted editable drafts, and explicit automation rules.

See [Communication Hub](communication-hub.md).

## Agents

Agents provides bounded persistent goals, plans, tools, communication access, retrieval, approvals, budgets, scheduling, event rules, run history, and an emergency stop.

See [Autonomous agents](autonomous-agents.md).
