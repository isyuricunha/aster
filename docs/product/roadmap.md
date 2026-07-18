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

Implementation and verification are recorded in [Aster interface redesign checklist](interface-redesign.md).

## Later stages

Routing analytics, controlled worker concurrency, authoritative provider usage accounting, additional providers, and specialized integrations remain planned improvements. They are not prerequisites for the bounded autonomous agent foundation and will be scheduled according to deployment feedback and operational need.
