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

## Milestone 6 - Structural visual overhaul

- [x] Re-review the latest reference images at full resolution and document their structural cues.
- [x] Replace the dashboard-style shell with compact window chrome and continuous work surfaces.
- [x] Replace the icon system and add shared motion, transition, and overlay behavior.
- [x] Redesign every configuration workspace around dense preference rows and editor surfaces.
- [x] Redesign chat, automation, agent, communication, and image workspaces at desktop density.
- [x] Browser-QA desktop, tablet, and mobile layouts and iterate on visual defects.
- [x] Re-run final lint, TypeScript, build, and UI contract checks.

## Milestone 7 - Readability and chat experience

- [x] Increase interface text contrast, type scale, line height, and reading width.
- [x] Add reduced-motion-safe shimmer treatment to key product headings.
- [x] Add chat onboarding, conversation starters, composer focus shortcuts, and auto-sizing input.
- [x] Integrate image generation and editing into the composer dock.
- [x] Repair mobile toolbar, navigation-label, switch, and overflow defects discovered in QA.
