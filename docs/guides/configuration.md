# Configuration

Aster separates runtime configuration from owner-managed application settings.

- `.env` controls deployment, storage, security, limits, and service behavior.
- The authenticated Settings workspace controls model endpoints, model roles, personas, tools, memory, knowledge, and the owner account.
- Credentials stored through the application are encrypted with `ASTER_ENCRYPTION_KEY`.

## Model endpoints

Open **Settings → Models** and add the API root for an OpenAI-compatible endpoint. Include `/v1` when required.

Aster may use:

```text
GET  {base_url}/models
POST {base_url}/chat/completions
POST {base_url}/embeddings
POST {base_url}/images/generations
POST {base_url}/images/edits
Authorization: Bearer <api-key>
```

Use **Test** before synchronizing the model catalog. Models may also be added manually when an endpoint does not expose `/models`.

## Model roles

Aster recognizes four explicit roles:

- **Primary** — chat, reasoning, interactive tool calls, default automation generation, and agent model fallback.
- **Utility** — bounded support work such as memory suggestions; resolves to Primary when unset.
- **Image** — image generation and editing.
- **Embedding** — optional semantic indexing and retrieval.

Only Primary is required for ordinary chat.

Per-model profiles declare chat and streaming support, token-field compatibility, reasoning effort, output limits, temperature, and top-p. Image profiles separately declare generation, editing, multiple-input, and mask support.

Model names are never used to guess capabilities.

## Fallbacks

The ordered fallback chain is global for chat-compatible generation.

A fallback is attempted only before any content or tool-call output has been emitted. Authentication and request-validation errors remain visible, and Aster never combines partial output from different models.

## Personas

Open **Settings → Personas** to create reusable identities with:

- name and description;
- instructions;
- enabled state;
- system or developer instruction placement;
- optional default selection.

New conversations copy the selected persona into a frozen snapshot. Editing the source persona does not rewrite existing conversations, automations, or queued agent runs.

## Tools and MCP

Open **Settings → Tools** to configure MCP servers.

Supported transports:

- Streamable HTTP;
- stdio when `ASTER_MCP_STDIO_ENABLED=true`.

Discovered tools start controlled by explicit enablement, new-conversation defaults, and confirmation policies. Conversation and agent scopes are separate.

HTTP headers and stdio environment values are encrypted and never returned by the API.

## Memory and knowledge

Open **Settings → Memory & Knowledge** to manage:

- approved global or persona-scoped memories;
- pending model-generated suggestions;
- knowledge collections;
- documents and indexing;
- the optional Embedding model;
- default and per-conversation retrieval scopes.

Lexical retrieval remains available without embeddings. Embedding failures do not delete lexical indexes or make documents unavailable.

## Images

Select an Image model or declare the required image capability on the Primary model. Configure image defaults only when the provider requires them.

Aster validates input and output formats, dimensions, byte limits, and signatures before storing private media.

## Automations, communications, and agents

These workspaces store their own definitions and encrypted integration credentials in PostgreSQL.

- Automations may use SMTP, CalDAV, inbound webhooks, and outbound webhooks.
- Communications may use IMAP and Discord accounts; email replies require an explicitly linked SMTP integration.
- Agents receive immutable per-run model, persona, tool, account, retrieval, approval, and budget scopes.

No model receives implicit access to tools, accounts, credentials, or side effects.

## Advanced settings

The default settings surfaces show common configuration. **Advanced settings** exposes maintenance controls, manual identifiers, low-level provider fields, import and export, reindexing, stdio, secrets, timeouts, deletion, and scope details.

## Runtime variables

See the complete [environment reference](../reference/environment.md). Recreate affected containers after changing `.env`:

```bash
docker compose up -d --force-recreate api worker web
```

Changing `ASTER_ENCRYPTION_KEY` without re-encrypting stored credentials makes those credentials unreadable.
