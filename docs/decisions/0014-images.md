# ADR-0014: Private image operations and media history

## Status

Proposed for Stage 14.

## Context

Aster needs image generation and editing without turning provider URLs into durable state, storing binary media inside chat text, exposing private outputs publicly, or introducing background jobs before they are required.

Image operations have different persistence, capability, and safety requirements from streamed text chat. Uploaded inputs, masks, generated outputs, provider parameters, model identity, failures, and conversation history must remain inspectable and independently deletable.

## Direction

Stage 14 will add a bounded private media store, explicit image-model capabilities, OpenAI-compatible image generation and editing, visual message attachments, persisted image operations, and an authenticated gallery.

The stage will not add generic multimodal chat, video, audio, public sharing, autonomous generation, scheduled image jobs, or application-wide mobile remediation.
