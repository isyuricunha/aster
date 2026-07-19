# Floating workspace windows

Aster keeps chat as the primary workspace while allowing selected tools to remain available without replacing the current page.

## Initial scope

The shared window manager controls three surfaces:

- Settings
- Communications
- Agents

Images and Automations remain normal routes until their interfaces are adapted deliberately.

## Behavior

- each window can be moved, resized, minimized, restored, closed, and focused independently
- active windows are ordered through an internal z-index stack
- minimized windows appear in one shared dock
- the last desktop size and position of each window are stored locally in the browser
- opening a window on a narrow screen minimizes other open windows and uses a full-screen surface
- Escape closes only the top visible window
- direct routes remain available through normal links and the Open page action

## Rendering model

Workspace windows use authenticated same-origin embedded routes. The embedded route removes the outer Aster navigation frame but keeps the original workspace component and API behavior. This avoids duplicating Communications or Agents logic inside the window manager.

Settings remains a special window with its own compact internal navigation. It uses the same shared focus, drag, resize, minimize, and dock behavior as other workspace windows.

## Boundaries

- window geometry is browser-local interface state and is not synchronized through the server
- closing a window does not alter its underlying Aster data
- minimizing a window removes its embedded document from view; restoring it may reload that workspace
- no autonomous action or additional permission is granted by opening a workspace window
