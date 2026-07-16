# ADR-0003: Global persona and canonical message composition

Status: Accepted

## Context

Aster needs one user-defined persona before chat is implemented. Persona text is written by the user, but it is instruction context. Treating it as an ordinary user message would pollute conversation history, weaken instruction priority, and make provider adapters harder to reason about.

The first chat milestone also needs a provider-neutral message representation that preserves the difference between role and origin.

## Decision

Aster stores one global persona with:

- a name
- free-form instructions
- an enabled flag
- an instruction role: `developer` or `system`

The persona is stored separately from conversations. When enabled, the message composer creates one canonical instruction message with `source=persona`. It never creates a `user` message for persona content.

A non-empty persona name is rendered as:

```text
Your name is <name>.
```

Free-form instructions follow as written. When the selected role is `system`, the content is wrapped in explicit `USER_DEFINED_PERSONA` delimiters so future adapters can merge system instructions without losing the content boundary.

Canonical messages carry both:

- `role`: `system`, `developer`, `user`, `assistant`, or `tool`
- `source`: `platform`, `persona`, `conversation`, `user`, `assistant`, or `tool`

The current user message is appended unchanged with `role=user` and `source=user`.

## Consequences

- Persona configuration remains auditable and independent from chat history.
- The chat milestone can consume one stable message-composition contract.
- APIs that support `developer` can receive the persona at that role.
- APIs limited to `system` can use the explicit system representation without rewriting the user message.
- Multiple personas, persona versioning, provider capability detection, and actual model requests remain deferred.
