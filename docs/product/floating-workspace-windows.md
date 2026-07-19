# Floating workspace windows

Aster keeps chat as the primary workspace while allowing the rest of the private product to remain available without replacing the current page.

## Scope

The shared window manager controls five surfaces:

- Settings
- Communications
- Agents
- Images
- Automations

Every surface also keeps its authenticated direct route as a full-page fallback.

## Behavior

- each window can be moved, resized, minimized, restored, closed, and focused independently
- active windows are ordered through an internal z-index stack
- minimized windows appear in one shared dock
- the last desktop size and position of each window are stored locally in the browser
- opening a window on a narrow screen minimizes other open windows and uses a full-screen surface
- Escape closes only the top visible window
- direct routes remain available through normal modified-click navigation and the Open page action

## Rendering model

Workspace windows use authenticated same-origin embedded routes. The embedded route removes the outer Aster navigation frame but keeps the original workspace component and API behavior. This avoids duplicating communication, agent, image, or automation logic inside the window manager.

Responsive behavior remains owned by each workspace. The embedded document viewport follows the resized window, so existing image gallery and automation layout breakpoints adapt naturally as the owner changes the window size.

Settings remains a special window with its own compact internal navigation. It uses the same shared focus, drag, resize, minimize, and dock behavior as the other workspace windows.

## Boundaries

- window geometry is browser-local interface state and is not synchronized through the server
- closing a window does not alter its underlying Aster data
- minimizing a window removes its embedded document from view; restoring it may reload that workspace
- opening a workspace window grants no autonomous action or additional permission
- chat remains the normal full-page root workspace rather than a nested floating window
