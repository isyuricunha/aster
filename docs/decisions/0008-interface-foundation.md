# ADR-0008: Interface foundation

## Status

Accepted for Stage 8.

## Context

The functional MVP grew through endpoint configuration, persona composition, persistent chat, deployment hardening, and single-owner authentication. Each milestone introduced usable screens, but the interface did not yet share a consistent navigation model, density, hierarchy, or interaction language.

The application is primarily used as a desktop workspace for long conversations and technical configuration. It must remain comfortable on mobile without turning the desktop experience into oversized cards and sparse marketing layouts.

## Decision

Aster uses one compact application frame with:

- a persistent workspace sidebar on desktop;
- a thin contextual toolbar;
- shared navigation for chat, models, persona, and account security;
- neutral dark surfaces with subtle borders;
- amber as the restrained product accent;
- compact controls and metadata rows;
- responsive navigation that becomes horizontal on narrow screens;
- a dependency-free internal icon set and Aster brand mark.

Chat remains a specialized full-height workspace but reuses the same navigation, tokens, icons, selected states, and surface hierarchy.

Authentication uses the same visual system while presenting a focused entry surface separated from the authenticated workspace.

## Consequences

- New screens should use the shared frame and existing interface tokens.
- Product hierarchy should rely on spacing, typography, and selected surfaces before adding decorative containers.
- Controls should remain compact enough for sustained desktop use.
- The interface must preserve keyboard focus visibility and usable touch targets.
- New UI dependencies require a separate decision; the Stage 8 foundation remains dependency-free.
- Visual changes must not alter authentication, persistence, streaming, endpoint, or persona contracts.
