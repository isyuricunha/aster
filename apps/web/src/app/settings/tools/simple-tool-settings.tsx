"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  apiRequest,
  type McpServer,
  type McpTool,
} from "../../../lib/api";
import { Icon } from "../../ui/icons";
import {
  notifySettingsUpdated,
  SummaryCard,
  SummaryGrid,
  UnsavedBadge,
  useUnsavedChanges,
} from "../settings-primitives";
import styles from "../simple-settings.module.css";

type ServerDraft = {
  id: string | null;
  name: string;
  url: string;
  enabled: boolean;
};

const blankServer: ServerDraft = {
  id: null,
  name: "",
  url: "",
  enabled: true,
};

function serverDraft(server: McpServer): ServerDraft {
  return {
    id: server.id,
    name: server.name,
    url: server.url ?? "",
    enabled: server.enabled,
  };
}

function sameServerDraft(left: ServerDraft, right: ServerDraft): boolean {
  return (
    left.id === right.id &&
    left.name === right.name &&
    left.url === right.url &&
    left.enabled === right.enabled
  );
}

export function SimpleToolSettings({
  initialServers,
  initialTools,
  initialError,
}: {
  initialServers: McpServer[];
  initialTools: McpTool[];
  initialError: string | null;
}) {
  const router = useRouter();
  const [servers, setServers] = useState(initialServers);
  const [tools, setTools] = useState(initialTools);
  const [draft, setDraft] = useState<ServerDraft>(blankServer);
  const [savedDraft, setSavedDraft] = useState<ServerDraft>(blankServer);
  const [toolQuery, setToolQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialError);

  const selectedServer = servers.find((server) => server.id === draft.id) ?? null;
  const dirty = !sameServerDraft(draft, savedDraft);
  const visibleTools = useMemo(() => {
    const query = toolQuery.trim().toLocaleLowerCase();
    if (!query) return tools;
    return tools.filter((tool) =>
      `${tool.name} ${tool.public_name} ${tool.server_name} ${tool.description}`
        .toLocaleLowerCase()
        .includes(query),
    );
  }, [toolQuery, tools]);
  useUnsavedChanges(dirty);

  function completeUpdate(message: string) {
    setNotice(message);
    notifySettingsUpdated();
    router.refresh();
  }

  async function refreshCatalog() {
    const [nextServers, nextTools] = await Promise.all([
      apiRequest<McpServer[]>("/api/mcp-servers"),
      apiRequest<McpTool[]>("/api/mcp-tools"),
    ]);
    setServers(nextServers);
    setTools(nextTools);
  }

  async function run(key: string, operation: () => Promise<void>) {
    if (busy) return;
    setBusy(key);
    setNotice(null);
    setError(null);
    try {
      await operation();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The operation failed.");
    } finally {
      setBusy(null);
    }
  }

  function editServer(server: McpServer) {
    if (server.transport !== "streamable_http") {
      setNotice("Stdio servers are edited from Advanced settings.");
      return;
    }
    const next = serverDraft(server);
    setDraft(next);
    setSavedDraft(next);
    setNotice(null);
    setError(null);
  }

  function resetServer() {
    setDraft(blankServer);
    setSavedDraft(blankServer);
  }

  async function saveServer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.name.trim() || !draft.url.trim()) {
      setError("Enter a server name and Streamable HTTP URL.");
      return;
    }
    await run("server-save", async () => {
      await apiRequest<McpServer>(
        draft.id ? `/api/mcp-servers/${draft.id}` : "/api/mcp-servers",
        {
          method: draft.id ? "PUT" : "POST",
          body: JSON.stringify({
            name: draft.name.trim(),
            transport: "streamable_http",
            url: draft.url.trim(),
            command: null,
            arguments: [],
            headers: {},
            environment: {},
            enabled: draft.enabled,
            timeout_seconds: selectedServer?.timeout_seconds ?? 30,
            ...(draft.id ? { preserve_secrets: true } : {}),
          }),
        },
      );
      await refreshCatalog();
      resetServer();
      completeUpdate(draft.id ? "MCP server updated." : "MCP server connected.");
    });
  }

  async function runServerAction(server: McpServer, action: "test" | "sync") {
    await run(`${action}:${server.id}`, async () => {
      const result = await apiRequest<{ tools_found: number; message?: string }>(
        `/api/mcp-servers/${server.id}/${action}`,
        { method: "POST" },
      );
      await refreshCatalog();
      completeUpdate(
        action === "sync"
          ? `Synchronized ${result.tools_found} tool(s) from ${server.name}.`
          : result.message ?? `${server.name} is reachable.`,
      );
    });
  }

  async function updateTool(tool: McpTool, patch: Partial<McpTool>) {
    await run(`tool:${tool.id}`, async () => {
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
      completeUpdate(`${tool.name} policy updated.`);
    });
  }

  return (
    <div aria-busy={busy !== null} className={styles.root}>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}
      {!error && notice ? <div className={styles.notice} role="status">{notice}</div> : null}

      <SummaryGrid>
        <SummaryCard
          label="Servers"
          value={`${servers.filter((server) => server.enabled).length}/${servers.length} enabled`}
          note={`${servers.filter((server) => server.last_sync_status === "succeeded").length} synchronized`}
        />
        <SummaryCard
          label="Tools"
          value={String(tools.length)}
          note={`${tools.filter((tool) => tool.is_available).length} available`}
        />
        <SummaryCard
          label="New chats"
          value={String(tools.filter((tool) => tool.enabled && tool.default_enabled).length)}
          note="Enabled by default"
        />
        <SummaryCard
          label="Confirmation"
          value={String(tools.filter((tool) => tool.enabled && tool.requires_confirmation).length)}
          note="Owner approval required"
        />
      </SummaryGrid>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Connect an MCP server</h2>
            <p>The simple flow uses Streamable HTTP and preserves existing encrypted headers.</p>
          </div>
          <UnsavedBadge visible={dirty} />
        </div>
        <form className={styles.sectionBody} onSubmit={saveServer}>
          <div className={styles.formGrid}>
            <label className={styles.field}>
              <span>Name</span>
              <input
                disabled={busy !== null}
                maxLength={120}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                placeholder="Filesystem tools"
                required
                value={draft.name}
              />
            </label>
            <label className={styles.field}>
              <span>Streamable HTTP URL</span>
              <input
                disabled={busy !== null}
                onChange={(event) => setDraft({ ...draft, url: event.target.value })}
                placeholder="https://mcp.example.com/mcp"
                required
                type="url"
                value={draft.url}
              />
            </label>
            <label className={styles.checkboxField}>
              <input
                checked={draft.enabled}
                disabled={busy !== null}
                onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
                type="checkbox"
              />
              Server enabled
            </label>
            <div className={styles.actions}>
              {draft.id || dirty ? (
                <button
                  className={styles.secondaryButton}
                  disabled={busy !== null}
                  onClick={resetServer}
                  type="button"
                >
                  Cancel
                </button>
              ) : null}
              <button className={styles.primaryButton} disabled={busy !== null} type="submit">
                {busy === "server-save"
                  ? "Saving server"
                  : draft.id
                    ? "Save server"
                    : "Connect server"}
              </button>
            </div>
          </div>
        </form>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Connected servers</h2>
            <p>Test connectivity or synchronize the tool catalog without opening technical fields.</p>
          </div>
        </div>
        <div className={styles.sectionBody}>
          <div className={styles.list}>
            {servers.length === 0 ? (
              <div className={styles.empty}>No MCP servers are configured yet.</div>
            ) : (
              servers.map((server) => (
                <article className={styles.row} key={server.id}>
                  <div className={styles.rowMain}>
                    <div className={styles.badges}>
                      <span
                        className={`${styles.badge} ${server.enabled ? styles.successBadge : styles.warningBadge}`}
                      >
                        {server.enabled ? "Enabled" : "Disabled"}
                      </span>
                      <span
                        className={`${styles.badge} ${
                          server.last_sync_status === "succeeded"
                            ? styles.successBadge
                            : server.last_sync_status === "failed"
                              ? styles.dangerBadge
                              : ""
                        }`}
                      >
                        {server.last_sync_status ?? "Not synced"}
                      </span>
                      <span className={styles.badge}>{server.transport}</span>
                    </div>
                    <strong>{server.name}</strong>
                    <p>{server.transport === "streamable_http" ? server.url : server.command}</p>
                    <small>
                      {server.available_tool_count}/{server.tool_count} tools available
                      {server.last_error ? ` · ${server.last_error}` : ""}
                    </small>
                  </div>
                  <div className={styles.rowActions}>
                    <button
                      className={styles.secondaryButton}
                      disabled={busy !== null || server.transport !== "streamable_http"}
                      onClick={() => editServer(server)}
                      type="button"
                    >
                      {server.transport === "streamable_http" ? "Edit" : "Advanced"}
                    </button>
                    <button
                      className={styles.secondaryButton}
                      disabled={busy !== null}
                      onClick={() => void runServerAction(server, "test")}
                      type="button"
                    >
                      {busy === `test:${server.id}` ? "Testing" : "Test"}
                    </button>
                    <button
                      className={styles.secondaryButton}
                      disabled={busy !== null}
                      onClick={() => void runServerAction(server, "sync")}
                      type="button"
                    >
                      {busy === `sync:${server.id}` ? "Syncing" : "Sync"}
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <div>
            <h2>Tool permissions</h2>
            <p>Enable tools, choose new-chat defaults, and keep confirmation where side effects matter.</p>
          </div>
          <label className={styles.field} style={{ minWidth: 190 }}>
            <span>Filter tools</span>
            <input
              onChange={(event) => setToolQuery(event.target.value)}
              placeholder="Search tools"
              type="search"
              value={toolQuery}
            />
          </label>
        </div>
        <div className={styles.sectionBody}>
          <div className={styles.list}>
            {visibleTools.length === 0 ? (
              <div className={styles.empty}>
                {tools.length ? "No tools match this filter." : "Synchronize a server to discover tools."}
              </div>
            ) : (
              visibleTools.map((tool) => (
                <article className={styles.row} key={tool.id}>
                  <div className={styles.rowMain}>
                    <div className={styles.badges}>
                      <span
                        className={`${styles.badge} ${tool.is_available ? styles.successBadge : styles.dangerBadge}`}
                      >
                        {tool.is_available ? "Available" : "Missing"}
                      </span>
                      <span className={styles.badge}>{tool.server_name}</span>
                    </div>
                    <strong>{tool.name}</strong>
                    <p>{tool.description || "No description was provided by the MCP server."}</p>
                    <small>{tool.public_name}</small>
                  </div>
                  <div className={styles.rowActions}>
                    <PolicyToggle
                      checked={tool.enabled}
                      disabled={!tool.is_available || busy !== null}
                      label="Enabled"
                      onChange={(value) => void updateTool(tool, { enabled: value })}
                    />
                    <PolicyToggle
                      checked={tool.default_enabled}
                      disabled={!tool.enabled || busy !== null}
                      label="New chats"
                      onChange={(value) => void updateTool(tool, { default_enabled: value })}
                    />
                    <PolicyToggle
                      checked={tool.requires_confirmation}
                      disabled={!tool.enabled || busy !== null}
                      label="Confirm"
                      onChange={(value) => void updateTool(tool, { requires_confirmation: value })}
                    />
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
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
    <label className={styles.checkboxField}>
      <input
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      {label}
    </label>
  );
}
