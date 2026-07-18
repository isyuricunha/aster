# Aster Roadmap

## Completed foundation

Stages 1 through 15 established the self-hosted application foundation: OpenAI-compatible model endpoints, personas, persistent chat, authentication, model profiles and fallbacks, export and search, interface refinement, persona snapshots, MCP tools, memory and RAG, images, and durable automations with outbound integrations.

## Stage 16 — Communication Hub

Stage 16 adds private inbound communication surfaces:

- IMAP email accounts and inbox synchronization
- Discord bots restricted to explicitly allowed channels
- persistent threads, messages, unread state, and private attachments
- manual email and Discord replies
- explicit communication-to-automation allowlist rules
- durable cursors, leases, deduplication, and audit history

Receiving content does not grant a model access to the account and does not permit automatic replies.

## Stage 17 — Autonomous Agents

Stage 17 adds bounded agents on top of the existing tools, memory, RAG, automations, and communication events:

- persistent goals, plans, and subtasks
- event-driven and scheduled execution
- explicit tool and channel scopes
- approval policies for sensitive actions
- step, time, token, and cost limits
- pause, resume, cancel, and emergency stop controls
- loop prevention and complete execution history

Agents must never inherit communication reply authority or tool permissions implicitly.

## Later stages

Mobile and narrow-screen remediation, routing analytics, additional providers, and specialized integrations remain planned improvements. They are not prerequisites for Stage 17 and will be scheduled according to deployment feedback and operational need.
