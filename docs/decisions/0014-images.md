# ADR-0014: Private image operations and media history

## Status

Accepted for Stage 14.

## Context

Aster needs image generation and editing without turning provider URLs into durable state, storing binary media inside chat text or PostgreSQL, exposing private outputs publicly, guessing capabilities from model names, or introducing background jobs before they are required.

Image operations have different persistence, capability, and safety requirements from streamed text chat. Uploaded inputs, masks, generated outputs, provider parameters, model identity, failures, file lifecycle, and conversation history must remain inspectable and independently controlled.

OpenAI-compatible image endpoints are not uniform. Some models generate but do not edit, some accept multiple inputs or masks, accepted parameter values differ, and results may contain either base64 data or temporary URLs.

## Decision

### Explicit operation mode

Image generation and editing use an explicit Image mode in the chat composer. Aster does not inspect ordinary user text for phrases such as “generate an image” and silently change execution paths.

A generated or edited result is represented by a normal user and assistant turn plus explicit attachment records. Text edit and regeneration remain unavailable for those turns; a new image operation preserves clearer lineage and parameters.

### Model selection and capabilities

The Image role selects the default image model. When it is empty, Aster may use the Primary model only when that exact cached model has an image profile declaring the required capability.

Image profiles declare:

- generation support;
- editing support;
- multiple-input support;
- mask support;
- maximum input count;
- normalized defaults for size, quality, output format, background, count, and input fidelity;
- bounded additional provider parameters.

Aster never infers image support from provider or model names.

### Provider contract

Aster uses the OpenAI-compatible routes:

```text
POST {base_url}/images/generations
POST {base_url}/images/edits
```

Generation requests use JSON. Editing requests use multipart form data with one or more image inputs and an optional mask.

Aster accepts base64 results and provider URLs. URL results are downloaded immediately, validated, and persisted. Remote URLs are never used as durable history.

Additional provider parameters are bounded and cannot override Aster-controlled fields such as model, prompt, inputs, mask, count, output format, or routing.

### Private media storage

Media bytes live in a private filesystem store mounted at `ASTER_MEDIA_ROOT`. The default Compose deployment uses the persistent `aster-media` volume.

PostgreSQL stores:

- media identity and storage key;
- original filename when applicable;
- media type, byte size, dimensions, and SHA-256 hash;
- image operations, status, prompt, revised prompt, model identity, parameters, errors, and timestamps;
- operation inputs and outputs;
- message attachments.

Media bytes are not stored in chat content, JSON columns, or PostgreSQL binary columns.

Content is served only through authenticated API routes. Original provider URLs and filesystem paths are not exposed.

### Validation and privacy

Stage 14 accepts PNG, JPEG, and WebP.

Aster validates magic bytes, structural boundaries, dimensions, maximum pixels, and maximum bytes. It removes supported private metadata containers before persistence and provider submission. SVG and generic arbitrary files are rejected.

Uploads use generated storage keys and atomic writes. A failed database transaction removes the corresponding file. Failed or interrupted operations remain visible without leaving partial outputs marked as completed.

### Persistence and history

Every operation is persisted before contacting the provider. Provider failures update the existing operation and assistant message to an explicit failed state.

Generated outputs are associated with the assistant turn. Editing inputs are associated with the user turn. The Images workspace is a second view over the same operation and asset records rather than an independent gallery database.

Deleting a conversation removes its generated output media. Standalone uploads can be deleted only while unreferenced.

Running operations discovered during startup are marked failed because Stage 14 does not introduce a background queue capable of resuming them.

### Conversation transfer

Portable conversation exports continue to use version 4. They do not contain private media bytes, provider URLs, filesystem paths, or attachment records. Affected turns receive an explicit omission note so imported transcripts do not imply that private media was transferred.

### Boundaries

Stage 14 does not add:

- generic multimodal chat or image understanding by the Primary model;
- video or audio generation;
- OCR;
- SVG uploads;
- public media links or sharing;
- canvas-based mask painting;
- image fallback chains;
- background queues or autonomous generation;
- scheduled image jobs;
- provider-native APIs that do not implement the declared OpenAI-compatible contract;
- application-wide mobile remediation.

## Consequences

- The default stack remains Next.js, FastAPI, PostgreSQL, and one private media volume.
- Image history survives application and container restarts.
- Provider differences are declared instead of guessed.
- Temporary provider URLs cannot expire out of the conversation history.
- Database backups and media backups are separate and both are required for a complete image restore.
- Synchronous image requests occupy one API request until the provider returns; background execution remains deferred.
- Conversation exports remain portable and bounded but intentionally do not clone private media libraries.
