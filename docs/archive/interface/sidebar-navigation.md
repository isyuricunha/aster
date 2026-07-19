# Unified application sidebar

Aster uses one application sidebar across chat and every full-page workspace. The navigation keeps frequent actions and conversation history close to the primary chat surface without duplicating route-specific sidebars.

## Information architecture

The sidebar is ordered by frequency of use:

1. product identity and the desktop collapse control
2. New chat and Search
3. expandable Chats history
4. Communications, Agents, Images, and Automations
5. owner identity and Settings in the fixed footer

Configuration pages are intentionally not repeated as a large navigation tree. The footer settings control opens the existing settings workspace, while the command palette remains available for direct access to individual settings sections.

## Conversation behavior

Chats expands inside the sidebar and remembers its open state locally in the browser. The initial list is bounded and may be extended with Show more.

Each conversation row provides:

- current-conversation state
- complete title through the native tooltip
- contextual rename and delete actions on hover or keyboard focus
- direct navigation from any full-page workspace
- conversation import from the Chats section action

The host refreshes conversation summaries when the browser regains focus, when the page becomes visible, and periodically while the application remains open. This keeps the global history current after chat mutations without introducing a new backend contract.

## Workspace behavior

A normal primary click opens Communications, Agents, Images, or Automations through the existing floating workspace manager. Modified clicks preserve standard browser navigation and open the full page directly.

Search opens the global command palette. The slash shortcut also opens the command palette when focus is not inside an editable control.

## Responsive behavior

On desktop, the sidebar may collapse into a narrow icon rail. The preference is stored locally and does not affect server data.

On narrow screens, the application reserves no permanent sidebar column. A shared trigger opens the same navigation as a modal drawer with focus containment, Escape handling, a backdrop, and body-scroll locking.

## Visual contract

The sidebar favors compact rows, precise alignment, restrained active states, subtle separators, and contextual actions instead of persistent cards or oversized controls. Product identity, colors, icons, labels, and feature names remain native to Aster.

## Embedded workspaces

Routes rendered with `?embedded=1` never mount the application sidebar. Floating workspace windows therefore continue to contain only their intended embedded content.

## Scope

This interface pass does not add or change backend endpoints, database migrations, permissions, credential scopes, model behavior, or autonomous execution. The route-specific sidebar markup remains temporarily available as a hidden compatibility fallback while the global navigation is validated in deployments.
