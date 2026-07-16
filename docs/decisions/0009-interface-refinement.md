# ADR-0009: Interface refinement through generated hierarchy

## Status

Accepted for Stage 8 refinement.

## Context

The first Stage 8 pass established a shared application frame, consistent navigation, and a dedicated visual language. Real browser review confirmed the direction, but the interface still relied too heavily on independently styled surfaces and visible borders.

The refinement needed to make the application feel like one continuous workspace rather than a collection of polished screens.

## Decision

Aster derives its dark interface from a small theme core:

- one neutral base;
- one restrained accent;
- one contrast target;
- semantic aliases for chrome, canvas, raised surfaces, selection, text, icons, and borders.

The sidebar and primary header form one application chrome around the active view. Hierarchy is expressed mainly through opacity, surface elevation, typography, and alignment instead of decorative gradients, large radii, or heavy shadows.

Navigation rows, conversation rows, controls, labels, and icons share common vertical rhythm and baseline alignment. Selected states remain visible without turning the accent into the dominant interface color.

The refinement remains dependency-free and does not change application behavior or API contracts.

## Consequences

The interface is denser, quieter, and more consistent across chat, settings, authentication, and responsive layouts. Future screens must use the semantic aliases and existing alignment rules instead of introducing isolated color or spacing systems.
