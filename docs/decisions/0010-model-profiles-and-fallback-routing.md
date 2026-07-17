# ADR-0010: Model profiles and fallback routing

## Status

Accepted for Stage 10.

## Context

Aster initially selected one primary model and sent every chat request with provider defaults. That kept the first chat implementation small, but it could not represent model-specific context, output, sampling, or reasoning settings. A temporary endpoint failure also ended the response even when another configured model could serve the request.

Provider-compatible APIs often expose similar generation controls with small naming differences. Fallback must also avoid combining output from different models into one message.

## Decision

Aster stores an optional profile for each cached model. A profile may define:

- a local display name;
- context-window and output-token metadata;
- temperature and top-p;
- the output-token field name used by the endpoint;
- reasoning effort;
- whether the model supports chat and streaming.

Unset generation values remain provider defaults and are omitted from the request.

Aster also stores one ordered chat fallback chain. The selected primary model is attempted first. Fallback models are attempted in the configured order only when:

- the failure indicates temporary unavailability or an incompatible chat stream; and
- the failed model has not emitted any response content.

Authentication and request-validation failures remain visible and do not trigger fallback. Once any content has been emitted, Aster never switches models for that response.

Unavailable, disabled, or non-streaming models are skipped while resolving the runtime chain. The provider model used for the completed response remains stored on the assistant message.

## Consequences

- Model behavior is configured once and reused by every chat request.
- Provider defaults remain safe because optional parameters are not invented.
- Fallback improves availability without hiding credential or profile mistakes.
- A response never contains content spliced from multiple models.
- The fallback chain is global for Stage 10; conversation-scoped routing remains a later extension.
