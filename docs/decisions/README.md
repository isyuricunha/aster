# Architecture decision records

Architecture decision records explain durable choices and their original context.

Accepted ADRs are historical documents. Update current guides and reference material when implementation evolves; do not silently rewrite an accepted decision to erase its original tradeoffs.

## Index

| Record | Decision |
| --- | --- |
| [0001](0001-initial-architecture.md) | Initial architecture |
| [0002](0002-model-endpoints-and-cache.md) | Model endpoints and cache |
| [0003](0003-persona-and-message-composition.md) | Persona and message composition |
| [0004](0004-persistent-chat-and-streaming.md) | Persistent chat and streaming |
| [0005](0005-chat-generation-lifecycle.md) | Chat generation lifecycle |
| [0006](0006-runtime-deployment-configuration.md) | Runtime deployment configuration |
| [0007](0007-single-owner-authentication.md) | Single-owner authentication |
| [0008](0008-interface-foundation.md) | Interface foundation |
| [0009-A](0009-interface-refinement.md) | Interface refinement |
| [0009-B](0009-chat-content-and-transfer.md) | Chat content and transfer |
| [0010](0010-model-profiles-and-fallback-routing.md) | Model profiles and fallback routing |
| [0011](0011-persona-library-and-conversation-snapshots.md) | Persona library and conversation snapshots |
| [0012](0012-tools-and-mcp.md) | Tools and MCP |
| [0013](0013-memory-and-rag.md) | Personal memory and bounded retrieval |
| [0014](0014-images.md) | Private image operations and media history |
| [0015](0015-automations-and-integrations.md) | Automations and integrations |
| [0016](0016-provider-instruction-roles.md) | Provider instruction roles |
| [0017](0017-communication-hub.md) | Communication Hub |
| [0018](0018-autonomous-agents.md) | Autonomous agents |
| [0019](0019-responsive-interface-system.md) | Responsive interface system |

## Historical numbering note

Two accepted records were independently assigned `0009` during early staged development. Their filenames and internal identifiers are preserved to avoid rewriting history and breaking old links. This index distinguishes them as `0009-A` and `0009-B`.

Future ADRs must use the next unused numeric identifier.

## Adding a decision

Use a short, durable document containing:

1. status;
2. context;
3. decision;
4. consequences;
5. rejected alternatives when they clarify the tradeoff.

Operational instructions belong in `docs/guides/` or `docs/reference/`, not in an ADR.
