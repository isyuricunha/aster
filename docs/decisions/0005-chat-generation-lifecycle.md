# ADR-0005: Linear chat replacement and generation lifecycle

## Status

Accepted.

## Context

The first chat milestone stored a linear user/assistant history and streamed one response at a time, but it did not support correction, regeneration, explicit cancellation, or recovery after an application restart.

Adding those controls without a conversation model would create ambiguous histories. A user could edit an old message while later responses still represented the old text, or regenerate an earlier answer while keeping later messages that depended on the previous answer.

## Decision

Aster keeps one linear history per conversation for MVP 1.

Editing a user message updates that message and removes every later message before requesting a replacement response. Regenerating an assistant response removes that response and every later message, then requests a new response from the user message immediately before it.

Only one response may be active in a conversation. Active generations are registered in the API process and can be stopped through an explicit endpoint. A stopped response is stored with the `stopped` status rather than being reported as an upstream failure.

Partial assistant output is checkpointed while streaming. On application startup, any message still marked as `streaming` is changed to `failed` with a sanitized interruption message. Completed, failed, stopped, and streaming messages remain distinct states; only completed messages are included in future model history.

## Consequences

- Message actions are deterministic and do not create hidden branches.
- Editing or regenerating an earlier message is destructive to the later conversation tail and the interface must state that clearly.
- Stop controls depend on the API process that owns the active stream. Startup recovery handles messages left behind when that process disappears.
- Multi-branch conversations and distributed generation coordination remain outside MVP 1.
