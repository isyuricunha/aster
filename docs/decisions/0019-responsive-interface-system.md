# ADR-0019: Responsive interface system

## Status

Accepted for the application-wide interface redesign.

## Context

Aster already uses a compact dark workspace, but its visual contracts evolved in layers. Shared tokens are split across multiple files, feature modules use aliases that are not defined, chat duplicates the main navigation, and narrow layouts reduce navigation to horizontal strips. The result is inconsistent hierarchy, incomplete keyboard focus treatment, undersized metadata, and avoidable mobile overflow.

The redesign must preserve every API and product behavior while giving chat, agents, automations, communications, images, settings, and authentication one coherent interface language.

## Decision

Aster adopts one dark, neutral interface system with a restrained warm accent.

### Theme core

The theme is generated from semantic roles rather than page-specific colors:

- chrome, canvas, subtle, raised, hover, and selected surfaces;
- subtle, default, strong, and control strokes;
- primary, secondary, muted, and disabled text;
- accent, positive, caution, negative, and informational states;
- explicit aliases for every legacy token while feature styles are migrated.

Functional text is never smaller than 12px. Controls use a 32–36px desktop rhythm and at least 44px for primary mobile targets. Focus is represented by a visible two-pixel accent ring and cannot rely on color fill alone.

### Layout model

- Wide desktop uses a persistent 232px navigation rail, an inset canvas, and optional master-detail panes.
- Compact desktop uses a 64px icon rail while preserving accessible names.
- Tablet uses a top bar and a navigation drawer instead of a horizontal destination strip.
- Mobile uses one `100dvh` pane, safe-area-aware fixed regions, and single-column task flows.

Chat keeps its state inside `ChatShell`. Shared chrome remains stateless and accepts chat-specific content through slots so streaming, search, import, rename, and focus behavior are not moved during the visual refactor.

### Interaction model

Shared components define rest, hover, pressed, selected, focus, disabled, busy, success, and error states. Status is always expressed with text or an icon in addition to color. Motion is short and nonessential, with reduced-motion, increased-contrast, and forced-color fallbacks.

### Responsive verification

Every route is checked at 360x800, 768x1024, 1024x768, and 1440x900. Validation includes keyboard navigation, touch targets, overflow, long content, empty data, loading, failures, destructive actions, and browser console errors.

## Consequences

- `interface-refinement.css` remains the final compatibility layer during the migration and becomes the canonical theme authority.
- Existing feature CSS files remain in place after browser verification; a separate cleanup may remove compatibility aliases once no longer referenced.
- New UI dependencies are unnecessary. The internal icon system and existing Next.js architecture remain intact.
- Mobile and narrow-screen remediation is part of this redesign rather than a deferred stage.
- Product behavior and backend contracts remain unchanged unless a UI audit exposed an existing state bug.
