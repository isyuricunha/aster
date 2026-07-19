# Simplified settings

Aster keeps configuration approachable without removing technical control. Each settings area now uses progressive disclosure: the common owner workflow is visible immediately, while the complete original interface remains available in an explicitly labeled advanced surface.

## Default surfaces

### Models

- connection summaries and endpoint health
- Primary, Utility, Image, and Embedding model roles
- ordered chat fallbacks
- basic endpoint creation and editing
- connection testing and model refresh

### Personas

- compact persona library
- name, description, instructions, and availability
- default persona selection for new conversations

### Memory and knowledge

- separate Memories, Documents, Collections, and Retrieval sections
- approved memory creation, editing, and deletion
- private document upload, status, reindexing, and deletion
- collection creation, editing, defaults, and deletion
- lexical or hybrid retrieval selection

### Tools

- Streamable HTTP server connection
- server health, testing, and synchronization
- searchable tool catalog
- enabled, new-chat default, and confirmation policies

### Account

- owner identity summary
- password change
- other-session revocation
- current-session sign-out

## Advanced settings

The advanced surface preserves all existing capabilities, including:

- manual model IDs, provider parameters, capability overrides, and endpoint deletion
- persona instruction roles, preview, import, export, duplication, deletion, and conversation snapshots
- memory suggestions, bulk import and export, bulk reindexing, and per-conversation retrieval scope
- MCP stdio transport, encrypted headers and environment values, timeouts, server deletion, and per-conversation tool scope

Advanced content is mounted only after the owner opens it. Saving through the simplified surface closes and unmounts the advanced surface before the server-rendered data is refreshed, preventing stale duplicate editors from remaining visible.

## Unsaved changes

Editable simplified forms show an explicit unsaved-changes badge. Browser navigation and tab closure use the native before-unload warning while a draft differs from its last saved state.

## Boundaries

- no backend endpoint, database schema, permission, secret handling, or runtime behavior changes
- no feature is deleted or made inaccessible
- advanced destructive and maintenance actions remain deliberate
- direct settings routes and embedded floating-window rendering continue to use the same components
