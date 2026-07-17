"use client";

import { useMemo, useState } from "react";

import {
  apiRequest,
  type ConversationSummary,
  type ConversationToolSettings,
  type McpServer,
  type McpTool,
} from "../../../lib/api";
import { Icon } from "../../ui/icons";
import styles from "./tools.module.css";

type ServerDraft = {
  name: string;
  transport: "streamable_http" | "stdio";
  url: string;
  command: string;
  arguments: string;
  headers: string;
  environment: string;
  enabled: boolean;
  timeoutSeconds: string;
  clearStoredSecrets: boolean;
};

const emptyDraft: ServerDraft = {
  name: "",
  transport: "streamable_http",
  url: "",
  command: "",
  arguments: "",
  headers: "",
  environment: "",
  enabled: true,
  timeoutSeconds: "30",
  clearStoredSecrets: false,
};

export function ToolSettings({
  initialServers,
  initialTools,
  initialConversations,
  initialError,
}: {
  initialServers: McpServer[];
  initialTools: McpTool[];
  initialConversations: ConversationSummary[];
  initialError: string | null;
}) {
  const [servers, setServers] = useState(initialServers);
  const [tools, setTools] = useState(initialTools);
  const [conversations] = useState(initialConversations);
  const [selectedServerId, setSelectedServerId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ServerDraft>(emptyDraft);
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [conversationToolIds, setConversationToolIds] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(initialError);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const selectedServer = useMemo(
    () => servers.find((server) => server.id === selectedServerId) ?? null,
    [selectedServerId, servers],
  );
  const enabledTools = useMemo(
    () => tools.filter((tool) => tool.enabled && tool.is_available),
    [tools],
  );

  function updateDraft<Key extends keyof ServerDraft>(key: Key, value: ServerDraft[Key]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function resetDraft() {
    setSelectedServerId(null);
    setDraft(emptyDraft);
  }

  function editServer(server: McpServer) {
    setSelectedServerId(server.id);
    setDraft({
      name: server.name,
      transport: server.transport,
      url: server.url ?? "",
      command: server.command ?? "",
      arguments: server.arguments.join("\n"),
      headers: "",
      environment: "",
      enabled: server.enabled,
      timeoutSeconds: String(server.timeout_seconds),
      clearStoredSecrets: false,
    });
    setError(null);
    setNotice(null);
  }

  async function refreshCatalog(message?: string) {
    const [nextServers, nextTools] = await Promise.all([
      apiRequest<McpServer[]>("/api/mcp-servers"),
      apiRequest<McpTool[]>("/api/mcp-tools"),
    ]);
    setServers(nextServers);
    setTools(nextTools);
    if (message) setNotice(message);
  }

  async function saveServer() {
    setBusyKey("server-save");
    setError(null);
    setNotice(null);
    try {
      const timeoutSeconds = Number.parseInt(draft.timeoutSeconds, 10);
      if (!Number.isFinite(timeoutSeconds)) throw new Error("Timeout must be a whole number.");
      const payload = {
        name: draft.name,
        transport: draft.transport,
        url: draft.transport === "streamable_http" ? draft.url : null,
        command: draft.transport === "stdio" ? draft.command : null,
        arguments: draft.transport === "stdio" ? parseLines(draft.arguments) : [],
        headers:
          draft.transport === "streamable_http" ? parseKeyValueLines(draft.headers, ":") : {},
        environment:
          draft.transport === "stdio" ? parseKeyValueLines(draft.environment, "=") : {},
        enabled: draft.enabled,
        timeout_seconds: timeoutSeconds,
        ...(selectedServerId ? { preserve_secrets: !draft.clearStoredSecrets } : {}),
      };
      if (selectedServerId) {
        await apiRequest<McpServer>(`/api/mcp-servers/${selectedServerId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await apiRequest<McpServer>("/api/mcp-servers", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      await refreshCatalog(selectedServerId ? "MCP server updated." : "MCP server created.");
      resetDraft();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the MCP server.");
    } finally {
      setBusyKey(null);
    }
  }

  async function runServerAction(server: McpServer, action: "test" | "sync") {
    setBusyKey(`${action}:${server.id}`);
    setError(null);
    setNotice(null);
    try {
      const result = await apiRequest<{ tools_found: number; message?: string }>(
        `/api/mcp-servers/${server.id}/${action}`,
        { method: "POST" },
      );
      await refreshCatalog(
        action === "sync"
          ? `Synchronized ${result.tools_found} tool(s) from ${server.name}.`
          : result.message ?? `${server.name} is reachable.`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not ${action} the MCP server.`);
      await refreshCatalog();
    } finally {
      setBusyKey(null);
    }
  }

  async function removeServer(server: McpServer) {
    if (!window.confirm(`Delete ${server.name} and every tool discovered from it?`)) return;
    setBusyKey(`delete:${server.id}`);
    setError(null);
    try {
      await apiRequest<void>(`/api/mcp-servers/${server.id}`, { method: "DELETE" });
      await refreshCatalog("MCP server deleted.");
      if (selectedServerId === server.id) resetDraft();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete the MCP server.");
    } finally {
      setBusyKey(null);
    }
  }

  async function updateTool(tool: McpTool, patch: Partial<McpTool>) {
    setBusyKey(`tool:${tool.id}`);
    setError(null);
    try {
      const next = {
        enabled: patch.enabled ?? tool.enabled,
        default_enabled: patch.default_enabled ?? tool.default_enabled,
        requires_confirmation: patch.requires_confirmation ?? tool.requires_confirmation,
      };
      if (!next.enabled) next.default_enabled = false;
      const updated = await apiRequest<McpTool>(`/api/mcp-tools/${tool.id}`, {
        method: "PUT",
        body: JSON.stringify(next),
      });
      setTools((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not update the tool policy.");
    } finally {
      setBusyKey(null);
    }
  }

  async function selectConversation(conversationId: string) {
    setSelectedConversationId(conversationId);
    setError(null);
    setNotice(null);
    if (!conversationId) {
      setConversationToolIds([]);
      return;
    }
    try {
      const scope = await apiRequest<ConversationToolSettings>(
        `/api/conversations/${conversationId}/tools`,
      );
      setConversationToolIds(scope.tools.map((tool) => tool.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load conversation tools.");
    }
  }

  async function saveConversationScope() {
    if (!selectedConversationId) return;
    setBusyKey("scope-save");
    setError(null);
    try {
      const result = await apiRequest<ConversationToolSettings>(
        `/api/conversations/${selectedConversationId}/tools`,
        {
          method: "PUT",
          body: JSON.stringify({ tool_ids: conversationToolIds }),
        },
      );
      setConversationToolIds(result.tools.map((tool) => tool.id));
      setNotice("Conversation tool scope saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save conversation tools.");
    } finally {
      setBusyKey(null);
    }
  }

  function toggleConversationTool(toolId: string) {
    setConversationToolIds((current) =>
      current.includes(toolId) ? current.filter((id) => id !== toolId) : [...current, toolId],
    );
  }

  return (
    <div className={styles.stack}>
      {notice ? <div className="notice success">{notice}</div> : null}
      {error ? <div className="notice error">{error}</div> : null}

      <section className={`panel ${styles.serverPanel}`}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">MCP servers</p>
            <h2>{selectedServer ? `Edit ${selectedServer.name}` : "Connect a server"}</h2>
            <p>
              Streamable HTTP works by default. Stdio is available only when the server owner enables
              it in Aster&apos;s runtime configuration.
            </p>
          </div>
          {selectedServer ? (
            <button className="button secondary" onClick={resetDraft} type="button">
              New server
            </button>
          ) : null}
        </div>

        <div className={styles.formGrid}>
          <label>
            <span>Name</span>
            <input
              value={draft.name}
              onChange={(event) => updateDraft("name", event.target.value)}
              placeholder="Filesystem tools"
            />
          </label>
          <label>
            <span>Transport</span>
            <select
              value={draft.transport}
              onChange={(event) =>
                updateDraft("transport", event.target.value as ServerDraft["transport"])
              }
            >
              <option value="streamable_http">Streamable HTTP</option>
              <option value="stdio">Stdio</option>
            </select>
          </label>
          <label>
            <span>Timeout seconds</span>
            <input
              inputMode="numeric"
              value={draft.timeoutSeconds}
              onChange={(event) => updateDraft("timeoutSeconds", event.target.value)}
            />
          </label>
          <label className={styles.checkboxLabel}>
            <input
              checked={draft.enabled}
              onChange={(event) => updateDraft("enabled", event.target.checked)}
              type="checkbox"
            />
            <span>Server enabled</span>
          </label>
        </div>

        {draft.transport === "streamable_http" ? (
          <div className={styles.transportFields}>
            <label>
              <span>Streamable HTTP URL</span>
              <input
                value={draft.url}
                onChange={(event) => updateDraft("url", event.target.value)}
                placeholder="https://mcp.example.com/mcp"
              />
            </label>
            <label>
              <span>HTTP headers</span>
              <textarea
                value={draft.headers}
                onChange={(event) => updateDraft("headers", event.target.value)}
                placeholder="Authorization: Bearer ...\nX-Workspace: aster"
                rows={4}
              />
              <small>
                One header per line. Saved values are encrypted and never loaded back into this form.
              </small>
            </label>
          </div>
        ) : (
          <div className={styles.transportFields}>
            <label>
              <span>Command</span>
              <input
                value={draft.command}
                onChange={(event) => updateDraft("command", event.target.value)}
                placeholder="python"
              />
            </label>
            <label>
              <span>Arguments</span>
              <textarea
                value={draft.arguments}
                onChange={(event) => updateDraft("arguments", event.target.value)}
                placeholder="-m\nmy_mcp_server"
                rows={4}
              />
              <small>One argument per line. Aster does not invoke a shell.</small>
            </label>
            <label>
              <span>Environment</span>
              <textarea
                value={draft.environment}
                onChange={(event) => updateDraft("environment", event.target.value)}
                placeholder="API_TOKEN=..."
                rows={4}
              />
              <small>One NAME=value pair per line. Values are encrypted at rest.</small>
            </label>
          </div>
        )}

        {selectedServer ? (
          <div className={styles.savedSecrets}>
            <span>
              Stored headers: {selectedServer.header_names.join(", ") || "none"} · Stored environment:
              {` ${selectedServer.environment_names.join(", ") || "none"}`}
            </span>
            <label className={styles.checkboxLabel}>
              <input
                checked={draft.clearStoredSecrets}
                onChange={(event) => updateDraft("clearStoredSecrets", event.target.checked)}
                type="checkbox"
              />
              <span>Clear stored values when saving</span>
            </label>
          </div>
        ) : null}

        <div className="form-actions">
          <button
            className="button primary"
            disabled={busyKey !== null}
            onClick={() => void saveServer()}
            type="button"
          >
            {busyKey === "server-save" ? "Saving..." : selectedServer ? "Save server" : "Add server"}
          </button>
          <button className="button secondary" onClick={resetDraft} type="button">
            Reset
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Connections</p>
            <h2>Configured servers</h2>
            <p>Test connectivity without changing the catalog, or synchronize to refresh tools.</p>
          </div>
        </div>
        <div className={styles.serverList}>
          {servers.length ? (
            servers.map((server) => (
              <article className={styles.serverRow} key={server.id}>
                <button className={styles.serverIdentity} onClick={() => editServer(server)} type="button">
                  <span className={styles.serverIcon}>
                    <Icon name="tools" size={15} />
                  </span>
                  <span>
                    <strong>{server.name}</strong>
                    <small>
                      {server.transport === "streamable_http" ? server.url : server.command} · {server.tool_count}
                      {server.tool_count === 1 ? " tool" : " tools"}
                    </small>
                  </span>
                </button>
                <div className={styles.serverStatus}>
                  <span className={`status-pill ${server.enabled ? "success" : "neutral"}`}>
                    {server.enabled ? "Enabled" : "Disabled"}
                  </span>
                  <span className={`status-pill ${server.last_sync_status === "failed" ? "danger" : "neutral"}`}>
                    {server.last_sync_status ?? "Not synced"}
                  </span>
                </div>
                <div className={styles.rowActions}>
                  <button
                    className="button secondary"
                    disabled={busyKey !== null}
                    onClick={() => void runServerAction(server, "test")}
                    type="button"
                  >
                    {busyKey === `test:${server.id}` ? "Testing..." : "Test"}
                  </button>
                  <button
                    className="button secondary"
                    disabled={busyKey !== null}
                    onClick={() => void runServerAction(server, "sync")}
                    type="button"
                  >
                    {busyKey === `sync:${server.id}` ? "Syncing..." : "Sync"}
                  </button>
                  <button
                    aria-label={`Delete ${server.name}`}
                    className="icon-button danger"
                    disabled={busyKey !== null}
                    onClick={() => void removeServer(server)}
                    type="button"
                  >
                    <Icon name="trash" size={14} />
                  </button>
                </div>
                {server.last_error ? <p className={styles.serverError}>{server.last_error}</p> : null}
              </article>
            ))
          ) : (
            <div className="empty-state">No MCP servers are configured yet.</div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Permissions</p>
            <h2>Discovered tools</h2>
            <p>New tools start disabled and require confirmation. Loosen that policy deliberately.</p>
          </div>
        </div>
        <div className={styles.toolList}>
          {tools.length ? (
            tools.map((tool) => (
              <article className={styles.toolRow} key={tool.id}>
                <div className={styles.toolIdentity}>
                  <strong>{tool.name}</strong>
                  <span>{tool.server_name}</span>
                  <p>{tool.description || "No description was provided by the MCP server."}</p>
                  <code>{tool.public_name}</code>
                </div>
                <div className={styles.policyGrid}>
                  <PolicyToggle
                    checked={tool.enabled}
                    disabled={!tool.is_available || busyKey === `tool:${tool.id}`}
                    label="Enabled"
                    onChange={(value) => void updateTool(tool, { enabled: value })}
                  />
                  <PolicyToggle
                    checked={tool.default_enabled}
                    disabled={!tool.enabled || busyKey === `tool:${tool.id}`}
                    label="New chats"
                    onChange={(value) => void updateTool(tool, { default_enabled: value })}
                  />
                  <PolicyToggle
                    checked={tool.requires_confirmation}
                    disabled={!tool.enabled || busyKey === `tool:${tool.id}`}
                    label="Confirm"
                    onChange={(value) => void updateTool(tool, { requires_confirmation: value })}
                  />
                </div>
                <span className={`status-pill ${tool.is_available ? "success" : "danger"}`}>
                  {tool.is_available ? "Available" : "Missing"}
                </span>
              </article>
            ))
          ) : (
            <div className="empty-state">Synchronize an MCP server to discover tools.</div>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Conversation scope</p>
            <h2>Assign tools to an existing chat</h2>
            <p>Changing this list affects later requests only. It does not rewrite previous tool history.</p>
          </div>
        </div>
        <label>
          <span>Conversation</span>
          <select
            value={selectedConversationId}
            onChange={(event) => void selectConversation(event.target.value)}
          >
            <option value="">Select a conversation</option>
            {conversations.map((conversation) => (
              <option key={conversation.id} value={conversation.id}>
                {conversation.title}
              </option>
            ))}
          </select>
        </label>
        {selectedConversationId ? (
          <div className={styles.scopeList}>
            {enabledTools.length ? (
              enabledTools.map((tool) => (
                <label className={styles.scopeItem} key={tool.id}>
                  <input
                    checked={conversationToolIds.includes(tool.id)}
                    onChange={() => toggleConversationTool(tool.id)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{tool.name}</strong>
                    <small>{tool.server_name}</small>
                  </span>
                </label>
              ))
            ) : (
              <div className="empty-state">No enabled tools are available.</div>
            )}
            <button
              className="button primary"
              disabled={busyKey !== null}
              onClick={() => void saveConversationScope()}
              type="button"
            >
              {busyKey === "scope-save" ? "Saving..." : "Save conversation tools"}
            </button>
          </div>
        ) : null}
      </section>
    </div>
  );
}

function PolicyToggle({
  checked,
  disabled,
  label,
  onChange,
}: {
  checked: boolean;
  disabled: boolean;
  label: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className={styles.policyToggle}>
      <input
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <span>{label}</span>
    </label>
  );
}

function parseLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function parseKeyValueLines(value: string, delimiter: ":" | "="): Record<string, string> {
  const result: Record<string, string> = {};
  for (const rawLine of value.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    const separator = line.indexOf(delimiter);
    if (separator <= 0) {
      throw new Error(`Invalid line: ${line}. Expected NAME${delimiter}value.`);
    }
    const name = line.slice(0, separator).trim();
    const item = line.slice(separator + 1).trim();
    if (!name || !item) throw new Error(`Invalid line: ${line}.`);
    result[name] = item;
  }
  return result;
}
