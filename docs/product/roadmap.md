# Aster Roadmap

## Completed foundation

Stages 1 through 16 established the self-hosted application foundation: OpenAI-compatible model endpoints, personas, persistent chat, authentication, model profiles and fallbacks, export and search, interface refinement, persona snapshots, MCP tools, memory and RAG, images, durable automations with outbound integrations, and private inbound email and Discord communication channels.

## Stage 17 — Autonomous Agents

Stage 17 adds bounded persistent agents on top of the existing tools, memory, RAG, automations, and communication events:

- persistent goals, plans, and subtasks
- manual, scheduled, and communication-event execution
- explicit MCP tool, communication account, and knowledge collection scopes
- immutable permissions and budgets for every queued run
- owner approvals for sensitive tools and communication replies
- step, model-call, action, runtime, token, and optional cost limits
- pause, resume, cancel, retry, and emergency stop controls
- loop prevention and complete execution history
- private completion and failure notifications

Agents never inherit communication reply authority, tools, accounts, knowledge collections, or approval-free side effects implicitly.

## Completed interface redesign

The application-wide dark interface and responsive UX redesign consolidates the visual token system, repairs incomplete feature styling, unifies application chrome, and completes mobile and narrow-screen behavior without changing backend contracts.

The floating workspace system keeps chat as the primary surface while Settings, Communications, Agents, Images, and Automations can be moved, resized, focused, minimized, restored, or opened as normal full pages.

Global command-palette navigation provides keyboard-first access to blank chats, workspaces, settings, and full-history conversation search without duplicating feature interfaces.

Progressive settings surfaces keep daily model, persona, memory, knowledge, tool, and account configuration concise while preserving every maintenance and technical control in lazily mounted advanced settings.

The unified application sidebar places New chat, Search, expandable conversation history, workspaces, owner identity, and Settings in one persistent navigation surface across chat and full-page workspaces. Desktop collapse and narrow-screen drawer behavior use the same information architecture.

Implementation and verification are recorded in [Aster interface redesign checklist](interface-redesign.md), [Floating workspace windows](floating-workspace-windows.md), [Command palette](command-palette.md), [Simplified settings](simplified-settings.md), and [Unified application sidebar](sidebar-navigation.md).

## Later stages

Further product stages remain intentionally unscheduled. New work should be chosen from deployment feedback and concrete owner workflows instead of adding speculative dashboards, routing policy, portability layers, or integrations without a demonstrated need.
