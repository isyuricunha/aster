# Aster interface redesign checklist

This checklist tracks the application-wide dark interface and responsive UX redesign.

## Milestone 1 - Audit and design direction

- [x] Inventory every route, shell, workspace, form, panel, and responsive breakpoint.
- [x] Review the supplied interface references and extract transferable hierarchy principles.
- [x] Confirm the existing lint, TypeScript, and production build baseline.
- [x] Identify undefined design tokens and broken CSS-module contracts.
- [x] Define the Aster-specific theme, type scale, geometry, motion, and layout model.

## Milestone 2 - Shared foundation and application chrome

- [x] Define the canonical semantic token set and legacy aliases.
- [x] Load and apply the application typography consistently.
- [x] Add shared focus, selection, disabled, busy, contrast, and reduced-motion behavior.
- [x] Unify application and chat navigation without moving chat state.
- [x] Replace horizontal mobile navigation with an accessible compact navigation pattern.
- [x] Refresh authentication and first-run surfaces.

## Milestone 3 - Product workspaces

- [x] Refresh chat, composer, transcript, tool, retrieval, and image-operation surfaces.
- [x] Repair and redesign the complete Automations workspace.
- [x] Normalize Agents, Communications, Images, and Settings workspaces.
- [x] Align master-detail, list, editor, inspector, empty, loading, success, and error states.

## Milestone 4 - UX and accessibility remediation

- [x] Add accessible names, field labels, busy state, and live feedback where missing.
- [x] Fix stale selections and initial-load state defects discovered during the audit.
- [x] Add route-level loading, error, and not-found experiences.
- [x] Verify keyboard order, visible focus, touch targets, overflow, and safe areas.

## Milestone 5 - Validation

- [x] Pass lint, TypeScript, and production build checks.
- [x] Pass targeted automated UI contract tests.
- [x] Browser-QA every route at desktop, tablet, and mobile viewports.
- [x] Confirm no source-brand copy, assets, or identifiers appear in the product.
- [x] Review the final diff for behavior, types, imports, exports, and documentation accuracy.
