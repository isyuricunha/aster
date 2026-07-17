# ADR-0011: Persona library and conversation snapshots

## Status

Accepted for Stage 11.

## Context

Aster originally stored one mutable global persona. Every model request read the latest value, which made configuration simple but prevented multiple reusable identities and caused old conversations to change behavior when the global persona was edited.

A persona library needs reusable source records, while conversations need stable instruction context that survives later edits, deletion, export, and import.

## Decision

Aster stores personas as reusable library records with:

- a stable UUID;
- name and description;
- free-form instructions;
- enabled state;
- system or developer instruction role.

One optional default persona is selected for new conversations. Creating a conversation copies the selected persona fields into nullable snapshot columns on the conversation. No persona is also a valid explicit state.

Chat generation reads only the conversation snapshot. It does not read the mutable library record during generation.

Reassigning a conversation copies a new snapshot for future requests. Existing messages are not rewritten. Deleting the source persona clears only the optional source reference through `ON DELETE SET NULL`; snapshot content remains available.

Persona transfer files use the versioned `aster-persona` format. Conversation JSON version 2 includes an optional persona snapshot, while version 1 imports remain supported.

The legacy `/api/persona` contract maps to the current default persona during the compatibility period.

## Consequences

- Multiple reusable assistant identities can coexist.
- New conversations inherit a deterministic default or no persona.
- Library edits cannot retroactively alter old conversations.
- Source deletion does not erase historical conversation identity.
- Conversation exports remain portable without requiring the original persona library.
- Reassignment affects future generation context without pretending old messages were produced by the new persona.
- Full persona revision history and automatic propagation remain later extensions.
