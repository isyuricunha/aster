"use client";

import {
  useCallback,
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
export type WorkspaceWindowKey =
  | "communications"
  | "email"
  | "skills"
  | "agents"
  | "images"
  | "automations";

type WindowKey = "settings" | WorkspaceWindowKey;
type WindowMode = "floating" | "maximized" | "docked-left" | "docked-right";

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

type WindowGeometry = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type WindowDefinition = {
  key: WindowKey;
  label: string;
  description: string;
  icon: IconName;
  href: string;
  defaultGeometry: WindowGeometry;
};

type FloatingWindowState = {
  open: boolean;
  minimized: boolean;
  zIndex: number;
  geometry: WindowGeometry;
  mode: WindowMode;
  href: string;
};

type WindowCollection = Record<WindowKey, FloatingWindowState>;

type DragState = {
  key: WindowKey;
  pointerId: number;
  originX: number;
  originY: number;
  startX: number;
  startY: number;
};

type SnapPreview = {
  key: WindowKey;
  mode: Exclude<WindowMode, "floating">;
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
const WORKSPACE_WINDOW_KEYS: readonly WorkspaceWindowKey[] = [
  "communications",
  "email",
  "skills",
  "agents",
  "images",
  "automations",
];
const WINDOW_KEYS: readonly WindowKey[] = ["settings", ...WORKSPACE_WINDOW_KEYS];
const SETTINGS_SECTION_STORAGE_KEY = "aster.settings-window-section";
const WINDOW_GEOMETRY_STORAGE_PREFIX = "aster.workspace-window-geometry.";
const WINDOW_MODE_STORAGE_PREFIX = "aster.workspace-window-mode.";

const WINDOW_DEFINITIONS: Record<WindowKey, WindowDefinition> = {
  settings: {
    key: "settings",
    label: "Settings",
    description: "Models, personas, memory, tools, and account controls",
    icon: "settings",
    href: "/settings/models",
    defaultGeometry: { x: 190, y: 82, width: 940, height: 700 },
  },
  communications: {
    key: "communications",
    label: "Connections",
    description: "Discord, external tools, calendars, and communication services",
    icon: "tools",
    href: "/connections",
    defaultGeometry: { x: 220, y: 92, width: 1040, height: 720 },
  },
  email: {
    key: "email",
    label: "Email",
    description: "Mailboxes, conversations, drafts, and account settings",
    icon: "email",
    href: "/email",
    defaultGeometry: { x: 205, y: 76, width: 1180, height: 760 },
  },
  skills: {
    key: "skills",
    label: "Skills",
    description: "Reusable instructions, tests, audits, and lifecycle controls",
    icon: "skills",
    href: "/skills",
    defaultGeometry: { x: 250, y: 104, width: 1080, height: 740 },
  },
  agents: {
    key: "agents",
    label: "Agents",
    description: "Goals, permissions, runs, approvals, and controls",
    icon: "tools",
    href: "/agents",
    defaultGeometry: { x: 280, y: 116, width: 1160, height: 760 },
  },
  images: {
    key: "images",
    label: "Images",
    description: "Private gallery, operation details, and model capabilities",
    icon: "images",
    href: "/images",
    defaultGeometry: { x: 310, y: 128, width: 1080, height: 720 },
  },
  automations: {
    key: "automations",
    label: "Tasks",
    description: "Built-in tasks, custom schedules, runs, and notifications",
    icon: "refresh",
    href: "/tasks",
    defaultGeometry: { x: 340, y: 140, width: 1140, height: 750 },
  },
};

const SETTINGS_ROUTES: readonly [string, SettingsSection][] = [
  ["/settings/models", "models"],
  ["/settings/persona", "persona"],
  ["/settings/memory", "memory"],
  ["/settings/tools", "tools"],
  ["/settings/account", "account"],
];

const WORKSPACE_ROUTES: readonly [string, WorkspaceWindowKey][] = [
  ["/email", "email"],
  ["/connections", "communications"],
  ["/communications", "communications"],
  ["/discord", "communications"],
  ["/skills", "skills"],
  ["/agents", "agents"],
  ["/images", "images"],
  ["/tasks", "automations"],
  ["/automations", "automations"],
];

function isSettingsSection(value: unknown): value is SettingsSection {
  return SETTINGS_ITEMS.some((item) => item.key === value);
}

function isWorkspaceWindowKey(value: unknown): value is WorkspaceWindowKey {
  return WORKSPACE_WINDOW_KEYS.includes(value as WorkspaceWindowKey);
}

function isWindowMode(value: unknown): value is WindowMode {
  return ["floating", "maximized", "docked-left", "docked-right"].includes(
    value as WindowMode,
  );
}

function isNarrowViewport(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches;
}

function routeMatches(pathname: string, route: string): boolean {
  return pathname === route || pathname.startsWith(`${route}/`);
}

function settingsSectionForPath(pathname: string): SettingsSection | null {
  const match = SETTINGS_ROUTES.find(([route]) => routeMatches(pathname, route));
  if (match) return match[1];
  return pathname === "/settings" ? "models" : null;
}

function workspaceWindowForPath(pathname: string): WorkspaceWindowKey | null {
  return WORKSPACE_ROUTES.find(([route]) => routeMatches(pathname, route))?.[1] ?? null;
}

function embeddedHref(href: string): string {
  const hashIndex = href.indexOf("#");
  const hash = hashIndex >= 0 ? href.slice(hashIndex) : "";
  const base = hashIndex >= 0 ? href.slice(0, hashIndex) : href;
  if (/(?:\?|&)embedded=1(?:&|$)/.test(base)) return href;
  return `${base}${base.includes("?") ? "&" : "?"}embedded=1${hash}`;
}

function clampGeometry(geometry: WindowGeometry): WindowGeometry {
  if (typeof window === "undefined") return geometry;

  const margin = 10;
  const availableWidth = Math.max(320, window.innerWidth - margin * 2);
  const availableHeight = Math.max(260, window.innerHeight - margin * 2);
  const minimumWidth = Math.min(620, availableWidth);
  const minimumHeight = Math.min(400, availableHeight);
  const width = Math.min(Math.max(geometry.width, minimumWidth), availableWidth);
  const height = Math.min(Math.max(geometry.height, minimumHeight), availableHeight);
  const visibleTitleWidth = Math.min(220, width);

  return {
    x: Math.min(
      Math.max(geometry.x, margin - width + visibleTitleWidth),
      window.innerWidth - visibleTitleWidth,
    ),
    y: Math.min(Math.max(geometry.y, margin), window.innerHeight - 42),
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

function readStoredMode(key: WindowKey): WindowMode {
  if (typeof window === "undefined") return "floating";
  const stored = window.localStorage.getItem(`${WINDOW_MODE_STORAGE_PREFIX}${key}`);
  return isWindowMode(stored) ? stored : "floating";
}

function persistGeometry(key: WindowKey, geometry: WindowGeometry): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    `${WINDOW_GEOMETRY_STORAGE_PREFIX}${key}`,
    JSON.stringify(geometry),
  );
}

function persistMode(key: WindowKey, mode: WindowMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(`${WINDOW_MODE_STORAGE_PREFIX}${key}`, mode);
}

function initialSettingsSection(): SettingsSection {
  if (typeof window === "undefined") return "models";
  const stored = window.localStorage.getItem(SETTINGS_SECTION_STORAGE_KEY);
  return isSettingsSection(stored) ? stored : "models";
}

function initialWindows(): WindowCollection {
  return Object.fromEntries(
    WINDOW_KEYS.map((key, index) => [
      key,
      {
        open: false,
        minimized: false,
        zIndex: 101 + index,
        geometry: readStoredGeometry(key),
        mode: readStoredMode(key),
        href: WINDOW_DEFINITIONS[key].href,
      },
    ]),
  ) as WindowCollection;
}

function highestZIndex(windows: WindowCollection): number {
  return Math.max(...WINDOW_KEYS.map((key) => windows[key].zIndex));
}

function highestVisibleZIndex(windows: WindowCollection): number {
  return Math.max(
    0,
    ...WINDOW_KEYS.filter((key) => windows[key].open && !windows[key].minimized).map(
      (key) => windows[key].zIndex,
    ),
  );
}

function viewportTopInset(): number {
  if (typeof window === "undefined") return 42;
  const raw = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue("--window-height");
  const value = Number.parseFloat(raw);
  return Number.isFinite(value) ? value : 42;
}

function snapModeForPointer(clientX: number, clientY: number): SnapPreview["mode"] | null {
  if (typeof window === "undefined" || isNarrowViewport()) return null;
  if (clientY <= viewportTopInset() + 18) return "maximized";
  if (clientX <= 18) return "docked-left";
  if (clientX >= window.innerWidth - 18) return "docked-right";
  return null;
}

export function WorkspaceWindowHost() {
  const dragState = useRef<DragState | null>(null);
  const windowElements = useRef(new Map<WindowKey, HTMLElement>());
  const [windows, setWindows] = useState<WindowCollection>(initialWindows);
  const [settingsSection, setSettingsSection] =
    useState<SettingsSection>(initialSettingsSection);
  const [snapPreview, setSnapPreview] = useState<SnapPreview | null>(null);

  const activeSettingsItem = useMemo(
    () => SETTINGS_ITEMS.find((item) => item.key === settingsSection) ?? SETTINGS_ITEMS[0],
    [settingsSection],
  );

  const openWindow = useCallback((key: WindowKey, requestedHref?: string) => {
    setWindows((current) => {
      const next = { ...current };
      if (isNarrowViewport()) {
        for (const otherKey of WINDOW_KEYS) {
          if (otherKey !== key && next[otherKey].open) {
            next[otherKey] = { ...next[otherKey], minimized: true };
          }
        }
      }

      const currentWindow = next[key];
      const href = requestedHref?.startsWith("/") ? requestedHref : currentWindow.href;
      next[key] = {
        ...currentWindow,
        open: true,
        minimized: false,
        zIndex: highestZIndex(current) + 1,
        geometry: clampGeometry(currentWindow.geometry),
        mode: isNarrowViewport() ? "maximized" : currentWindow.mode,
        href,
      };
      return next;
    });
  }, []);

  useEffect(() => {
    function handleSettingsOpen(event: Event) {
      const requestedSection = (event as CustomEvent<{ section?: unknown }>).detail?.section;
      if (isSettingsSection(requestedSection)) {
        setSettingsSection(requestedSection);
        window.localStorage.setItem(SETTINGS_SECTION_STORAGE_KEY, requestedSection);
      }
      openWindow("settings");
    }

    function handleWorkspaceOpen(event: Event) {
      const detail = (event as CustomEvent<{ window?: unknown; href?: unknown }>).detail;
      if (!isWorkspaceWindowKey(detail?.window)) return;
      const href = typeof detail.href === "string" ? detail.href : undefined;
      openWindow(detail.window, href);
    }

    function handleResize() {
      setWindows((current) => {
        const next = { ...current };
        for (const key of WINDOW_KEYS) {
          const geometry = clampGeometry(current[key].geometry);
          next[key] = { ...current[key], geometry };
          persistGeometry(key, geometry);
        }
        return next;
      });
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setWindows((current) => {
        const visible = WINDOW_KEYS.filter(
          (key) => current[key].open && !current[key].minimized,
        ).sort((left, right) => current[right].zIndex - current[left].zIndex);
        const top = visible[0];
        return top ? { ...current, [top]: { ...current[top], open: false } } : current;
      });
    }

    function handleInternalNavigation(event: MouseEvent) {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey ||
        !(event.target instanceof Element)
      ) {
        return;
      }

      const candidate = event.target.closest("a[href]");
      if (!(candidate instanceof HTMLAnchorElement)) return;
      if (
        candidate.dataset.asterFullPage === "true" ||
        candidate.hasAttribute("download") ||
        (candidate.target && candidate.target !== "_self")
      ) {
        return;
      }

      const url = new URL(candidate.href, window.location.href);
      if (url.origin !== window.location.origin) return;

      const requestedSettings = settingsSectionForPath(url.pathname);
      if (requestedSettings) {
        event.preventDefault();
        window.dispatchEvent(
          new CustomEvent(OPEN_SETTINGS_EVENT, {
            detail: { section: requestedSettings },
          }),
        );
        return;
      }

      const requestedWindow = workspaceWindowForPath(url.pathname);
      if (!requestedWindow) return;
      event.preventDefault();
      window.dispatchEvent(
        new CustomEvent(OPEN_WORKSPACE_WINDOW_EVENT, {
          detail: {
            window: requestedWindow,
            href: `${url.pathname}${url.search}${url.hash}`,
          },
        }),
      );
    }

    window.addEventListener(OPEN_SETTINGS_EVENT, handleSettingsOpen);
    window.addEventListener(OPEN_WORKSPACE_WINDOW_EVENT, handleWorkspaceOpen);
    window.addEventListener("resize", handleResize);
    window.addEventListener("keydown", handleEscape);
    document.addEventListener("click", handleInternalNavigation, true);
    return () => {
      window.removeEventListener(OPEN_SETTINGS_EVENT, handleSettingsOpen);
      window.removeEventListener(OPEN_WORKSPACE_WINDOW_EVENT, handleWorkspaceOpen);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("keydown", handleEscape);
      document.removeEventListener("click", handleInternalNavigation, true);
    };
  }, [openWindow]);

  useEffect(() => {
    const root = document.documentElement;
    for (const key of WINDOW_KEYS) {
      root.classList.toggle(`aster-window-${key}-open`, windows[key].open);
    }
    const visible = WINDOW_KEYS.filter(
      (key) => windows[key].open && !windows[key].minimized,
    );
    root.classList.toggle(
      "aster-workspace-focus-mode",
      visible.some((key) => windows[key].mode !== "floating"),
    );
    root.classList.toggle(
      "aster-workspace-docked-left",
      visible.some((key) => windows[key].mode === "docked-left"),
    );
    root.classList.toggle(
      "aster-workspace-docked-right",
      visible.some((key) => windows[key].mode === "docked-right"),
    );
  }, [windows]);

  useEffect(
    () => () => {
      const root = document.documentElement;
      for (const key of WINDOW_KEYS) root.classList.remove(`aster-window-${key}-open`);
      root.classList.remove(
        "aster-workspace-focus-mode",
        "aster-workspace-docked-left",
        "aster-workspace-docked-right",
      );
    },
    [],
  );

  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const key = entry.target.getAttribute("data-window-key");
        if (!WINDOW_KEYS.includes(key as WindowKey)) continue;
        const windowKey = key as WindowKey;
        const rect = entry.target.getBoundingClientRect();
        setWindows((current) => {
          if (current[windowKey].mode !== "floating") return current;
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
  }, [
    windows.settings.open,
    windows.communications.open,
    windows.email.open,
    windows.skills.open,
    windows.agents.open,
    windows.images.open,
    windows.automations.open,
  ]);

  function chooseSettingsSection(nextSection: SettingsSection) {
    setSettingsSection(nextSection);
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

  function setWindowMode(key: WindowKey, mode: WindowMode) {
    persistMode(key, mode);
    setWindows((current) => ({
      ...current,
      [key]: {
        ...current[key],
        minimized: false,
        mode,
        zIndex: highestZIndex(current) + 1,
      },
    }));
  }

  function toggleMaximize(key: WindowKey) {
    setWindowMode(key, windows[key].mode === "maximized" ? "floating" : "maximized");
  }

  function startDrag(key: WindowKey, event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0 || isNarrowViewport()) return;
    focusWindow(key);
    const state = windows[key];
    let geometry = state.geometry;

    if (state.mode !== "floating") {
      geometry = clampGeometry({
        ...geometry,
        x: event.clientX - Math.min(geometry.width * 0.45, 240),
        y: Math.max(viewportTopInset() + 8, event.clientY - 18),
      });
      persistMode(key, "floating");
      setWindows((current) => ({
        ...current,
        [key]: {
          ...current[key],
          geometry,
          mode: "floating",
          zIndex: highestZIndex(current) + 1,
        },
      }));
    }

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
    const mode = snapModeForPointer(event.clientX, event.clientY);
    setSnapPreview(mode ? { key: drag.key, mode } : null);
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

    const mode = event.type === "pointercancel" ? null : snapModeForPointer(event.clientX, event.clientY);
    setSnapPreview(null);
    if (mode) {
      setWindowMode(drag.key, mode);
      return;
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
    return key === "settings" ? activeSettingsItem.href : windows[key].href;
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
  const activeZIndex = highestVisibleZIndex(windows);

  return (
    <>
      <div className="workspace-window-layer">
        {snapPreview ? (
          <div
            aria-hidden="true"
            className={`workspace-snap-preview mode-${snapPreview.mode}`}
          />
        ) : null}

        {WINDOW_KEYS.map((key) => {
          const state = windows[key];
          if (!state.open || state.minimized) return null;
          const definition = WINDOW_DEFINITIONS[key];
          const href = windowHref(key);
          const subtitle = windowSubtitle(key);
          const icon = windowIcon(key);
          const active = state.zIndex === activeZIndex;

          return (
            <section
              aria-label={`${definition.label} window`}
              aria-modal="false"
              className={`workspace-floating-window workspace-floating-window-${key} mode-${state.mode} ${
                active ? "is-active" : ""
              }`}
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
                  onDoubleClick={() => toggleMaximize(key)}
                  onPointerCancel={finishDrag}
                  onPointerDown={(event) => startDrag(key, event)}
                  onPointerMove={continueDrag}
                  onPointerUp={finishDrag}
                >
                  <Icon name={icon} size={14} />
                  <div>
                    <strong>{definition.label}</strong>
                    <span>{subtitle}</span>
                  </div>
                </div>
                <div className="workspace-window-controls">
                  <details className="workspace-window-placement">
                    <summary aria-label={`Place ${definition.label} window`} title="Window placement">
                      <Icon name="more" size={14} />
                    </summary>
                    <div>
                      <button
                        disabled={state.mode === "floating"}
                        onClick={(event) => {
                          setWindowMode(key, "floating");
                          event.currentTarget.closest("details")?.removeAttribute("open");
                        }}
                        type="button"
                      >
                        <Icon name="unfocus" size={13} />
                        Float
                      </button>
                      <button
                        disabled={state.mode === "docked-left"}
                        onClick={(event) => {
                          setWindowMode(key, "docked-left");
                          event.currentTarget.closest("details")?.removeAttribute("open");
                        }}
                        type="button"
                      >
                        <Icon name="dock-left" size={13} />
                        Dock left
                      </button>
                      <button
                        disabled={state.mode === "docked-right"}
                        onClick={(event) => {
                          setWindowMode(key, "docked-right");
                          event.currentTarget.closest("details")?.removeAttribute("open");
                        }}
                        type="button"
                      >
                        <Icon name="dock-right" size={13} />
                        Dock right
                      </button>
                      <a data-aster-full-page="true" href={href}>
                        <Icon name="expand-panel" size={13} />
                        Open full page
                      </a>
                    </div>
                  </details>
                  <button
                    aria-label={
                      state.mode === "maximized"
                        ? `Restore ${definition.label}`
                        : `Maximize ${definition.label}`
                    }
                    onClick={() => toggleMaximize(key)}
                    title={state.mode === "maximized" ? "Restore" : "Maximize"}
                    type="button"
                  >
                    <Icon name={state.mode === "maximized" ? "unfocus" : "focus"} size={14} />
                  </button>
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
                    <Icon name="close" size={14} />
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
                    <iframe
                      key={settingsSection}
                      src={embeddedHref(activeSettingsItem.href)}
                      title={`${activeSettingsItem.label} settings`}
                    />
                  </div>
                </div>
              ) : (
                <div className="workspace-window-content">
                  <iframe
                    key={state.href}
                    src={embeddedHref(state.href)}
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
