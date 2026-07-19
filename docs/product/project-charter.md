# Aster project charter

Status: Active

## Vision

Aster is a private, self-hosted AI workspace for one owner.

It begins with reliable chat and grows only through concrete owner workflows. The product may connect models, tools, knowledge, media, communications, automations, and agents, but each capability must remain explicit, bounded, inspectable, and provider-neutral.

## Product principles

### Owner-controlled identity and context

The owner chooses personas, model endpoints, memory, knowledge collections, tools, accounts, integrations, automations, and agents.

No personal identity, private endpoint, relationship, credential, or provider-specific assumption is embedded in source code, fixtures, examples, or public documentation.

Model-generated memory suggestions remain pending until the owner accepts them.

### Explicit authority

User content, tool results, retrieved documents, communication messages, media metadata, webhook payloads, and agent observations are untrusted data.

They may provide facts but cannot grant themselves instruction priority, credentials, tools, accounts, reply permission, or side-effect authority.

### Provider-neutral contracts

OpenAI-compatible APIs are the preferred contracts for chat, embeddings, and images. MCP is the preferred external-tool contract. SMTP, CalDAV, IMAP, Discord, and HTTP are protocol integrations rather than hard-coded provider products.

Behavior is selected through declared capabilities and explicit configuration, never model-name guessing.

### Predictable generation

Generation settings are model-scoped. Unset values preserve provider defaults.

Fallback improves availability only before output begins. Aster never combines partial output from different models in one response.

Reasoning may be displayed to the owner when a provider supplies it, but it is not recycled into later conversation history.

### Frozen scopes

Personas are frozen into conversations and automations. Agent permissions, budgets, tools, accounts, retrieval, and approval policies are frozen into each queued run.

Editing a reusable definition changes future work only.

### Bounded side effects

Aster owns confirmation, execution, persistence, limits, retries, and audit history.

Automatic retry stops before uncertain external delivery side effects are repeated. AI-assisted communication replies remain editable and require an explicit send action.

### Durable self-hosting

PostgreSQL stores durable application state and queue ownership. Private media is stored outside the database in a shared local volume.

The default deployment does not require Redis, Celery, RabbitMQ, a separate vector database, or public object storage.

### Workspace clarity

Aster is one coherent daily-use application, not a collection of admin forms.

Navigation, density, visual hierarchy, focus behavior, keyboard access, responsive behavior, and error presentation must remain consistent across every workspace.

The product keeps common actions visible and moves maintenance complexity behind progressive disclosure.

### Small, verifiable changes

Changes should be focused, reversible, documented, and validated immediately.

Small iterative work may land directly on `main`. Destructive, schema-heavy, security-sensitive, or difficult-to-review work should use an isolated branch.

No unrelated work continues on top of a failing commit.

## Current product surface

Aster currently includes:

- persistent streamed chat with reasoning disclosure and generation feedback;
- endpoint catalogs, model roles, profiles, and ordered fallbacks;
- personas and frozen snapshots;
- MCP tools, confirmation, scopes, and execution history;
- approved memory, private collections, documents, lexical retrieval, and optional embeddings;
- private image generation, editing, gallery, and chat attachments;
- durable automations and external integrations;
- private IMAP and Discord communications with manual and AI-assisted replies;
- bounded persistent agents with approvals, budgets, schedules, event rules, and emergency stop;
- single-owner authentication and encrypted stored credentials;
- a unified sidebar, command palette, floating workspaces, compact settings, and responsive navigation.

## Current non-goals

The following are not current product commitments:

- multiple users, invitations, teams, or per-user tenancy;
- public media hosting or social sharing;
- automatic acceptance or autonomous maintenance of personal memory;
- unrestricted browsing, browser automation, or arbitrary web crawling;
- generic audio and video workspaces;
- provider billing reconciliation;
- speculative usage dashboards;
- automatic cost- or latency-based model routing;
- arbitrary visual workflow graphs;
- silently autonomous external side effects;
- a provider-specific plugin marketplace.

These non-goals may change only when a concrete owner workflow justifies the added complexity and security surface.

## Definition of done

A capability is complete only when:

1. its authority and data boundaries are explicit;
2. failures are visible without exposing secrets;
3. data is durable or deliberately ephemeral;
4. limits and recovery behavior are defined;
5. the web and API contracts are tested;
6. migrations and deployment behavior are validated;
7. current guides and reference documentation are updated;
8. the real self-hosted deployment behaves as expected.
