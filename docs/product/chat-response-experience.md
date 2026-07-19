# Chat response experience

Aster keeps message submission responsive before the first model token arrives and separates optional model reasoning from the final answer.

## Conversation creation

- A blank conversation is persisted before its first generation request starts.
- Successful conversation creation notifies the shared application sidebar immediately.
- The new conversation therefore appears in navigation independently of model latency or generation success.

## Generation feedback

- Every send, edit-and-resend, and regeneration marks the transcript busy immediately.
- The transcript displays `Generating answer…` with a restrained shimmer before the assistant message exists.
- Once the streaming assistant message is available, the feedback moves into that message.
- The feedback disappears when final answer content begins.
- Reduced-motion preferences replace the animation with static status text.

## Reasoning disclosure

- OpenAI-compatible `reasoning_content`, `reasoning`, `thinking`, and `analysis` stream fields are recognized.
- Reasoning items embedded in structured content arrays are recognized as well.
- Tagged `<think>`, `<analysis>`, and `<reasoning>` blocks remain compatible.
- Reasoning is displayed in a collapsed disclosure by default and can be expanded by the owner.
- Reasoning remains available after reload, stop, or failure without requiring a separate database column.
- Persisted reasoning is removed from prior assistant messages before the conversation history is sent back to a model.

## Scope

This behavior does not expose private reasoning outside the owner workspace, change model selection, add autonomous actions, or require a database migration.
