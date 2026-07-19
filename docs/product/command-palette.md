# Command palette

Aster exposes one global command palette for fast navigation without replacing the current workspace or duplicating feature interfaces.

## Opening the palette

- press `Ctrl+K` on Windows and Linux
- press `Command+K` on macOS
- select the shortcut control in the shared workspace title bar
- the palette is unavailable on setup and sign-in routes

## Commands

The palette groups results into:

- quick actions, including a blank new chat
- workspace navigation for Chat, Communications, Agents, Images, and Automations
- direct settings access for Models, Personas, Memory & Knowledge, Tools, and Account
- recent or matching conversations

Workspace and settings commands reuse the existing floating-window events. They do not create parallel interfaces or grant additional permissions.

## Conversation search

Opening the palette loads the current conversation list through the authenticated same-origin API. Entering a query uses the existing full-history conversation search, so results may match conversation titles or persisted message content.

Search requests are debounced and stale responses are ignored. The palette limits rendered conversation results while the API remains the authority for matching and ordering.

## Keyboard behavior

- `Arrow Up` and `Arrow Down` change the selected result
- `Home` and `End` move to the first or last result
- `Enter` opens the selected result
- `Escape` closes the palette without closing a workspace window behind it
- pressing the palette shortcut again toggles it closed

The global shortcut is captured before page-specific handlers. The existing `/` shortcut in chat continues to focus conversation search.

## Boundaries

- opening a workspace command does not change backend state
- opening a settings command does not save configuration
- conversation results remain private and require the owner session
- the palette is a navigation surface, not an autonomous action interface
- no new API, database migration, credential scope, or external side effect is introduced
