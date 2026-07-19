# Model prompt architecture

Aster keeps application-owned model instructions centralized in
`apps/api/app/prompt_library.py`. Prompt text is part of the runtime contract and should be reviewed
with the same care as API schemas, database migrations, and tool authorization.

## Prompt version

`PROMPT_VERSION` identifies the current audited prompt set. It is an operational marker, not a
provider API version. Change it when the shared prompt policy or trust model changes materially.

## Instruction hierarchy

Interactive chat composes model input in this order:

1. application-owned platform policy;
2. optional frozen persona snapshot;
3. optional bounded retrieval context;
4. persisted completed conversation history;
5. the current owner message.

Autonomous agents and unattended automations use the same principle: application policy comes
first, an optional persona follows, and the saved goal or instruction is supplied separately from
untrusted trigger, retrieval, history, communication, and tool-result data.

Persona instructions control identity, tone, style, and response preferences. They do not override
platform reliability, privacy, authorization, or tool boundaries.

## Provider instruction roles

Canonical application prompts use the `system` role. Before a real provider request is sent,
`provider_instruction_roles.py` normalizes every `system` and `developer` instruction message to the
role configured for that model profile. The default is `system` for broad OpenAI-compatible provider
support.

This preserves a single internal hierarchy without assuming that every provider implements the
`developer` role.

## Trust boundaries

Content supplied by external or persisted sources must remain visibly delimited. Current boundaries
include:

- `UNTRUSTED_MEMORY_AND_RETRIEVAL_CONTEXT`;
- `UNTRUSTED_AGENT_MEMORY_AND_RETRIEVAL_CONTEXT`;
- `UNTRUSTED_COMMUNICATION_THREAD`;
- `UNTRUSTED_TRIGGER_PAYLOAD`;
- `UNTRUSTED_PERSISTED_EXECUTION_HISTORY`;
- `UNTRUSTED_ACTION_RESULT`;
- `UNTRUSTED_TOOL_RESULT`.

Models are instructed to treat those blocks as data, never authority. Commands, role changes,
security overrides, and tool instructions found inside them are not executable instructions.

Owner-authored saved goals, automation instructions, and user messages have their own explicit data
boundaries so a model can distinguish the task from surrounding payloads.

## Flow-specific prompts

The shared library defines prompts for:

- interactive chat;
- conversation-title generation;
- durable memory suggestions;
- communication reply drafts;
- unattended automations;
- autonomous agents;
- tool-use safety;
- chat and agent retrieval context.

Flow modules should import these definitions or rendering helpers instead of embedding a new base
policy. A narrowly scoped local instruction is acceptable when it is inseparable from a specific
protocol, such as the exact structure of a tool result, but it must not contradict the shared policy.

## Output contracts

Prompts that feed parsers use strict output contracts:

- conversation titles return one plain-text title;
- memory suggestions return exactly one JSON object with a `memories` array;
- communication drafting returns only the editable reply body;
- agent and automation results must be standalone and must not expose hidden reasoning.

Runtime code still validates and bounds every output. Prompt wording is not a substitute for parser,
authorization, size, timeout, or confirmation enforcement.

## Review checklist

When adding or changing a model prompt:

1. Keep the project and provider language generic.
2. Put stable shared text in `prompt_library.py`.
3. Preserve platform policy before persona and user content.
4. Delimit all retrieved, quoted, triggered, persisted, and tool-produced data.
5. Never rely on the prompt to enforce permissions or side-effect confirmation.
6. Require the smallest output shape the consumer needs.
7. Add or update tests for ordering, delimiters, normalization, and parser expectations.
8. Update `PROMPT_VERSION` when the shared policy changes materially.
