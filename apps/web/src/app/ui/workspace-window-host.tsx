"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { Icon, type IconName } from "./icons";

export const OPEN_SETTINGS_EVENT = "aster:open-settings";
export const OPEN_WORKSPACE_WINDOW_EVENT = "aster:open-workspace-window";

export type SettingsSection = "models" | "persona" | "memory" | "tools" | "account";
export type WorkspaceWindowKey = "communications" | "agents";

type WindowKey = "settings" | WorkspaceWindowKey;

type SettingsItem = {
  key: SettingsSection;
  label: string;
  description: string;
  icon: IconName;
  href: string;
};

type SettingsGroup = {
  label: string;
  items: readonly SettingsItem[];
};

type WindowDefinition = {
  key: WindowKey;
  label: string;
  description: string;
  icon: IconName;
  href: string;
  defaultGeometry: WindowGeometry;
};

type WindowGeometry = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type FloatingWindowState = {
  open: boolean;
  minimized: boolean;
  zIndex: number;
  geometry: WindowGeometry;
};

type WindowCollection = Record<WindowKey, FloatingWindowState>;
type LoadingCollection = Record<WindowKey, boolean>;

type DragState = {
  key: WindowKey;
  pointerId: number;
  originX: number;
  originY: number;
  startX: number;
  startY: number;
};

const SETTINGS_GROUPS: readonly SettingsGroup[] = [
  {
    label: "AI",
    items: [
      {
        key: "models",
        label: "Models",
        description: "Endpoints, roles, profiles, and fallbacks",
        icon: "models",
        href: "/settings/models",
      },
      {
        key: "persona",
        label: "Personas",
        description: "Reusable identities and defaults",
        icon: "persona",
        href: "/settings/persona",
      },
      {
        key: "memory",
        label: "Memory & Knowledge",
        description: "Approved memory, documents, and retrieval",
        icon: "memory",
        href: "/settings/memory",
      },
    ],
  },
  {
    label: "Capabilities",
    items: [
      {
        key: "tools",
        label: "Tools",
        description: "MCP servers, scopes, and confirmations",
        icon: "tools",
        href: "/settings/tools",
      },
    ],
  },
  {
    label: "Workspace",
    items: [
      {
        key: "account",
        label: "Account",
        description: "Owner password and active sessions",
        icon: "account",
        href: "/settings/account",
      },
    ],
  },
];

const SETTINGS_ITEMS = SETTINGS_GROUPS.flatMap((group) => group.items);
const WINDOW_KEYS: readonly WindowKey[] = ["settings", "communications", "agents"];
const SETTINGS_SECTION_STORAGE_KEY = "aster.settings-window-section";
const WINDOW_GEOMETRY_STORAGE_PREFIX = "aster.workspace-window-geometry.";

const WINDOW_DEFINITIONS: Record<WindowKey, WindowDefinition> = {
  settings: {
    key: "settings",
    label: "Settings",
    description: "Models, personas, memory, tools, and account controls",
    icon: "settings",
    href: "/settings/models",
    defaultGeometry: { x: 190, y: 82, width: 980, height: 720 },
  },
  communications: {
    key: "communications",
    label: "Communications",
    description: "Email, Discord, accounts, and communication rules",
    icon: "chat",
    href: "/communications",
    defaultGeometry: { x: 225, y: 94, width: 1160, height: 760 },
  },
  agents: {
    key: "agents",
    label: "Agents",
    description: "Goals, permissions, runs, approvals, and controls",
    icon: "tools",
    href: "/agents",
    defaultGeometry: { x: 260, y: 106, width: 1200, height: 780 },
  },
};

function isSettingsSection(value: unknown): value is SettingsSection {
  return SETTINGS_ITEMS.some((item) => item.key === value);
}

function isWorkspaceWindowKey(value: unknown): value is WorkspaceWindowKey {
  return value === "communications" || value === "agents";
}

function isNarrowViewport(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches;
}

function clampGeometry(geometry: WindowGeometry): WindowGeometry {
  if (typeof window === "undefined") return geometry;

  const margin = 12;
  const availableWidth = Math.max(320, window.innerWidth - margin * 2);
  const availableHeight = Math.max(260, window.innerHeight - margin * 2);
  const minimumWidth = Math.min(680, availableWidth);
  const minimumHeight = Math.min(460, availableHeight);
  const width = Math.min(Math.max(geometry.width, minimumWidth), availableWidth);
  const height = Math.min(Math.max(geometry.height, minimumHeight), availableHeight);
  const visibleTitleWidth = Math.min(220, width);

  return {
    x: Math.min(
      Math.max(geometry.x, margin - width + visibleTitleWidth),
      window.innerWidth - visibleTitleWidth,
    ),
    y: Math.min(Math.max(geometry.y, margin), window.innerHeight - 52),
    width,
    height,
  };
}

function readStoredGeometry(key: WindowKey): WindowGeometry {
  const fallback = WINDOW_DEFINITIONS[key].defaultGeometry;
  if (typeof window === "undefined") return fallback;

  const stored = window.localStorage.getItem(`${WINDOW_GEOMETRY_STORAGE_PREFIX}${key}`);
  if (!stored) return clampGeometry(fallback);

  try {
    const parsed = JSON.parse(stored) as Partial<WindowGeometry>;
    if (
      typeof parsed.x === "number" &&
      typeof parsed.y === "number" &&
      typeof parsed.width === "number" &&
      typeof parsed.height === "number"
    ) {
      return clampGeometry({
        x: parsed.x,
        y: parsed.y,
        width: parsed.width,
        height: parsed.height,
      });
    }
  } catch {
    window.localStorage.removeItem(`${WINDOW_GEOMETRY_STORAGE_PREFIX}${key}`);
  }

  return clampGeometry(fallback);
}

function persistGeometry(key: WindowKey, geometry: WindowGeometry): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    `${WINDOW_GEOMETRY_STORAGE_PREFIX}${key}`,
    JSON.stringify(geometry),
  );
}

function initialSettingsSection(): SettingsSection {
  if (typeof window === "undefined") return "models";
  const stored = window.localStorage.getItem(SETTINGS_SECTION_STORAGE_KEY);
  return isSettingsSection(stored) ? stored : "models";
}

function initialWindows(): WindowCollection {
  return {
    settings: {
      open: false,
      minimized: false,
      zIndex: 101,
      geometry: readStoredGeometry("settings"),
    },
    communications: {
      open: false,
      minimized: false,
      zIndex: 102,
      geometry: readStoredGeometry("communications"),
    },
    agents: {
      open: false,
      minimized: false,
      zIndex: 103,
      geometry: readStoredGeometry("agents"),
    },
  };
}

function highestZIndex(windows: WindowCollection): number {
  return Math.max(...WINDOW_KEYS.map((key) => windows[key].zIndex));
}

export function WorkspaceWindowHost() {
  const dragState = useRef<DragState | null>(null);
  const windowElements = useRef(new Map<WindowKey, HTMLElement>());
  const [windows, setWindows] = useState<WindowCollection>(initialWindows);
  const [loading, setLoading] = useState<LoadingCollection>({
    settings: false,
    communications: false,
    agents: false,
  });
  const [settingsSection, setSettingsSection] =
    useState<SettingsSection>(initialSettingsSection);

  const activeSettingsItem = useMemo(
    () => SETTINGS_ITEMS.find((item) => item.key === settingsSection) ?? SETTINGS_ITEMS[0],
    [settingsSection],
  );

  useEffect(() => {
    function openWindow(key: WindowKey) {
      setLoading((current) => ({ ...current, [key]: true }));
      setWindows((current) => {
        const nextZIndex = highestZIndex(current) + 1;
        const next = { ...current };
        if (isNarrowViewport()) {
          for (const otherKey of WINDOW_KEYS) {
            if (otherKey !== key && next[otherKey].open) {
              next[otherKey] = { ...next[otherKey], minimized: true };
            }
          }
        }
        next[key] = {
          ...next[key],
          open: true,
          minimized: false,
          zIndex: nextZIndex,
          geometry: clampGeometry(next[key].geometry),
        };
        return next;
      });
    }

    const handleSettingsOpen = (event: Event) => {
      const requestedSection = (event as CustomEvent<{ section?: unknown }>).detail?.section;
      if (isSettingsSection(requestedSection)) {
        setSettingsSection(requestedSection);
        window.localStorage.setItem(SETTINGS_SECTION_STORAGE_KEY, requestedSection);
      }
      openWindow("settings");
    };

    const handleWorkspaceOpen = (event: Event) => {
      const requestedWindow = (event as CustomEvent<{ window?: unknown }>).detail?.window;
      if (isWorkspaceWindowKey(requestedWindow)) openWindow(requestedWindow);
    };

    const handleResize = () => {
      setWindows((current) => {
        const next = { ...current };
        for (const key of WINDOW_KEYS) {
          const geometry = clampGeometry(current[key].geometry);
          next[key] = { ...current[key], geometry };
          persistGeometry(key, geometry);
        }
        return next;
      });
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setWindows((current) => {
        const visible = WINDOW_KEYS.filter(
          (key) => current[key].open && !current[key].minimized,
        ).sort((left, right) => current[right].zIndex - current[left].zIndex);
        const top = visible[0];
        if (!top) return current;
        return { ...current, [top]: { ...current[top], open: false } };
      });
    };

    window.addEventListener(OPEN_SETTINGS_EVENT, handleSettingsOpen);
    window.addEventListener(OPEN_WORKSPACE_WINDOW_EVENT, handleWorkspaceOpen);
    window.addEventListener("resize", handleResize);
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener(OPEN_SETTINGS_EVENT, handleSettingsOpen);
      window.removeEventListener(OPEN_WORKSPACE_WINDOW_EVENT, handleWorkspaceOpen);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("keydown", handleEscape);
    };
  }, []);

  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const key = entry.target.getAttribute("data-window-key");
        if (!WINDOW_KEYS.includes(key as WindowKey)) continue;
        const windowKey = key as WindowKey;
        const rect = entry.target.getBoundingClientRect();
        setWindows((current) => {
          const existing = current[windowKey].geometry;
          const nextGeometry = clampGeometry({
            x: existing.x,
            y: existing.y,
            width: rect.width,
            height: rect.height,
          });
          if (
            Math.abs(existing.width - nextGeometry.width) < 1 &&
            Math.abs(existing.height - nextGeometry.height) < 1
          ) {
            return current;
          }
          persistGeometry(windowKey, nextGeometry);
          return {
            ...current,
            [windowKey]: { ...current[windowKey], geometry: nextGeometry },
          };
        });
      }
    });

    for (const element of windowElements.current.values()) observer.observe(element);
    return () => observer.disconnect();
  }, [windows.settings.open, windows.communications.open, windows.agents.open]);

  function chooseSettingsSection(nextSection: SettingsSection) {
    setSettingsSection(nextSection);
    setLoading((current) => ({ ...current, settings: true }));
    window.localStorage.setItem(SETTINGS_SECTION_STORAGE_KEY, nextSection);
  }

  function focusWindow(key: WindowKey) {
    setWindows((current) => {
      if (current[key].zIndex === highestZIndex(current)) return current;
      return {
        ...current,
        [key]: { ...current[key], zIndex: highestZIndex(current) + 1 },
      };
    });
  }

  function minimizeWindow(key: WindowKey) {
    setWindows((current) => ({
      ...current,
      [key]: { ...current[key], minimized: true },
    }));
  }

  function restoreWindow(key: WindowKey) {
    setWindows((current) => ({
      ...current,
      [key]: {
        ...current[key],
        minimized: false,
        zIndex: highestZIndex(current) + 1,
      },
    }));
  }

  function closeWindow(key: WindowKey) {
    setWindows((current) => ({
      ...current,
      [key]: { ...current[key], open: false, minimized: false },
    }));
  }

  function startDrag(key: WindowKey, event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0 || isNarrowViewport()) return;
    focusWindow(key);
    const geometry = windows[key].geometry;
    dragState.current = {
      key,
      pointerId: event.pointerId,
      originX: event.clientX,
      originY: event.clientY,
      startX: geometry.x,
      startY: geometry.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function continueDrag(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragState.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    setWindows((current) => {
      const geometry = current[drag.key].geometry;
      return {
        ...current,
        [drag.key]: {
          ...current[drag.key],
          geometry: clampGeometry({
            ...geometry,
            x: drag.startX + event.clientX - drag.originX,
            y: drag.startY + event.clientY - drag.originY,
          }),
        },
      };
    });
  }

  function finishDrag(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragState.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragState.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setWindows((current) => {
      const geometry = clampGeometry(current[drag.key].geometry);
      persistGeometry(drag.key, geometry);
      return {
        ...current,
        [drag.key]: { ...current[drag.key], geometry },
      };
    });
  }

  function windowHref(key: WindowKey): string {
    return key === "settings" ? activeSettingsItem.href : WINDOW_DEFINITIONS[key].href;
  }

  function windowSubtitle(key: WindowKey): string {
    return key === "settings"
      ? activeSettingsItem.label
      : WINDOW_DEFINITIONS[key].description;
  }

  function windowIcon(key: WindowKey): IconName {
    return key === "settings" ? activeSettingsItem.icon : WINDOW_DEFINITIONS[key].icon;
  }

  const minimizedWindows = WINDOW_KEYS.filter(
    (key) => windows[key].open && windows[key].minimized,
  );

  return (
    <>
      <div className="workspace-window-layer">
        {WINDOW_KEYS.map((key) => {
          const state = windows[key];
          if (!state.open || state.minimized) return null;
          const definition = WINDOW_DEFINITIONS[key];
          const href = windowHref(key);
          const subtitle = windowSubtitle(key);
          const icon = windowIcon(key);

          return (
            <section
              aria-label={`${definition.label} window`}
              aria-modal="false"
              className={`workspace-floating-window workspace-floating-window-${key}`}
              data-window-key={key}
              key={key}
              onPointerDown={() => focusWindow(key)}
              ref={(element) => {
                if (element) windowElements.current.set(key, element);
                else windowElements.current.delete(key);
              }}
              role="dialog"
              style={{
                height: state.geometry.height,
                left: state.geometry.x,
                top: state.geometry.y,
                width: state.geometry.width,
                zIndex: state.zIndex,
              }}
            >
              <header className="workspace-window-titlebar">
                <div
                  className="workspace-window-drag-handle"
                  onPointerCancel={finishDrag}
                  onPointerDown={(event) => startDrag(key, event)}
                  onPointerMove={continueDrag}
                  onPointerUp={finishDrag}
                >
                  <Icon name={icon} size={15} />
                  <div>
                    <strong>{definition.label}</strong>
                    <span>{subtitle}</span>
                  </div>
                </div>
                <div className="workspace-window-controls">
                  <a href={href} title={`Open ${definition.label} as a full page`}>
                    Open page
                  </a>
                  <button
                    aria-label={`Minimize ${definition.label}`}
                    onClick={() => minimizeWindow(key)}
                    title="Minimize"
                    type="button"
                  >
                    <span aria-hidden="true">−</span>
                  </button>
                  <button
                    aria-label={`Close ${definition.label}`}
                    onClick={() => closeWindow(key)}
                    title="Close"
                    type="button"
                  >
                    <Icon name="close" size={15} />
                  </button>
                </div>
              </header>

              {key === "settings" ? (
                <div className="settings-window-body">
                  <nav aria-label="Settings sections" className="settings-window-navigation">
                    <p className="settings-window-intro">
                      Essential controls first. Advanced options stay inside their own section.
                    </p>
                    {SETTINGS_GROUPS.map((group) => (
                      <section key={group.label}>
                        <h2>{group.label}</h2>
                        <div>
                          {group.items.map((item) => (
                            <button
                              aria-current={settingsSection === item.key ? "page" : undefined}
                              className={settingsSection === item.key ? "active" : ""}
                              key={item.key}
                              onClick={() => chooseSettingsSection(item.key)}
                              type="button"
                            >
                              <Icon name={item.icon} size={15} />
                              <span>
                                <strong>{item.label}</strong>
                                <small>{item.description}</small>
                              </span>
                            </button>
                          ))}
                        </div>
                      </section>
                    ))}
                  </nav>
                  <div className="workspace-window-content">
                    {loading.settings ? (
                      <div className="workspace-window-loading">
                        Loading {activeSettingsItem.label}…
                      </div>
                    ) : null}
                    <iframe
                      key={settingsSection}
                      onLoad={() =>
                        setLoading((current) => ({ ...current, settings: false }))
                      }
                      src={`${activeSettingsItem.href}?embedded=1`}
                      title={`${activeSettingsItem.label} settings`}
                    />
                  </div>
                </div>
              ) : (
                <div className="workspace-window-content">
                  {loading[key] ? (
                    <div className="workspace-window-loading">
                      Loading {definition.label}…
                    </div>
                  ) : null}
                  <iframe
                    onLoad={() => setLoading((current) => ({ ...current, [key]: false }))}
                    src={`${definition.href}?embedded=1`}
                    title={`${definition.label} workspace`}
                  />
                </div>
              )}
            </section>
          );
        })}
      </div>

      {minimizedWindows.length ? (
        <div aria-label="Minimized workspace windows" className="workspace-window-dock">
          {minimizedWindows.map((key) => {
            const definition = WINDOW_DEFINITIONS[key];
            return (
              <div key={key}>
                <button onClick={() => restoreWindow(key)} type="button">
                  <Icon name={windowIcon(key)} size={15} />
                  <span>{definition.label}</span>
                  {key === "settings" ? <small>{activeSettingsItem.label}</small> : null}
                </button>
                <button
                  aria-label={`Close ${definition.label}`}
                  onClick={() => closeWindow(key)}
                  type="button"
                >
                  <Icon name="close" size={13} />
                </button>
              </div>
            );
          })}
        </div>
      ) : null}
    </>
  );
}
