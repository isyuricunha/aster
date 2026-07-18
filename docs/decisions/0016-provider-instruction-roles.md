# ADR-0016: Provider instruction roles

## Status

Accepted

## Context

Aster targets generic OpenAI-compatible endpoints. The `developer` message role is useful for providers that implement newer OpenAI semantics, but many otherwise compatible servers support only the conventional `system`, `user`, `assistant`, and `tool` roles.

Persona, retrieval, tool-safety, automation, memory, and utility prompts all contain instruction messages. Handling their provider role independently would create inconsistent compatibility and make fallback behavior depend on the call path.

## Decision

Aster keeps canonical instruction sources internally, but normalizes every outbound `system` or `developer` instruction message to the role configured for the selected model profile.

- `system` is the default for maximum compatibility.
- `developer` is an explicit per-model opt-in.
- Primary, Utility, fallback, automation, memory, title, retrieval, and tool calls use the same provider normalization.
- User-defined persona text remains delimited regardless of its stored persona role.
- Provider-role selection never changes persisted conversation history.

## Consequences

Generic OpenAI-compatible endpoints receive conventional `system` instructions by default. Models with verified `developer` support can opt in without changing personas or application features. Fallback models may use a different instruction role from the Primary model because role selection is resolved per endpoint and model.
