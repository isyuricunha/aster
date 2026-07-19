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

type SettingsSection = "models" | "persona" | "memory" | "tools" | "account";

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
const POSITION_STORAGE_KEY = "aster.settings-window-position";
const SECTION_STORAGE_KEY = "aster.settings-window-section";

type WindowPosition = { x: number; y: number };

type DragState = {
  pointerId: number;
  originX: number;
  originY: number;
  startX: number;
  startY: number;
};

function isSettingsSection(value: unknown): value is SettingsSection {
  return SETTINGS_ITEMS.some((item) => item.key === value);
}

function clampPosition(position: WindowPosition): WindowPosition {
  if (typeof window === "undefined") return position;
  const margin = 12;
  const minimumVisibleWidth = 280;
  const minimumVisibleHeight = 54;
  return {
    x: Math.min(
      Math.max(position.x, margin - minimumVisibleWidth),
      window.innerWidth - minimumVisibleWidth,
    ),
    y: Math.min(
      Math.max(position.y, margin),
      window.innerHeight - minimumVisibleHeight,
    ),
  };
}

function initialSection(): SettingsSection {
  if (typeof window === "undefined") return "models";
  const saved = window.localStorage.getItem(SECTION_STORAGE_KEY);
  return isSettingsSection(saved) ? saved : "models";
}

function initialPosition(): WindowPosition {
  const fallback = { x: 190, y: 82 };
  if (typeof window === "undefined") return fallback;
  const saved = window.localStorage.getItem(POSITION_STORAGE_KEY);
  if (!saved) return clampPosition(fallback);
  try {
    const parsed = JSON.parse(saved) as Partial<WindowPosition>;
    if (typeof parsed.x === "number" && typeof parsed.y === "number") {
      return clampPosition({ x: parsed.x, y: parsed.y });
    }
  } catch {
    window.localStorage.removeItem(POSITION_STORAGE_KEY);
  }
  return clampPosition(fallback);
}

export function SettingsWindowHost() {
  const dragState = useRef<DragState | null>(null);
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [section, setSection] = useState<SettingsSection>(initialSection);
  const [position, setPosition] = useState<WindowPosition>(initialPosition);
  const [loading, setLoading] = useState(false);

  const activeItem = useMemo(
    () => SETTINGS_ITEMS.find((item) => item.key === section) ?? SETTINGS_ITEMS[0],
    [section],
  );

  useEffect(() => {
    const handleOpen = (event: Event) => {
      const requestedSection = (event as CustomEvent<{ section?: unknown }>).detail?.section;
      if (isSettingsSection(requestedSection)) {
        setSection(requestedSection);
        window.localStorage.setItem(SECTION_STORAGE_KEY, requestedSection);
      }
      setOpen(true);
      setMinimized(false);
      setLoading(true);
    };
    const handleResize = () => setPosition((current) => clampPosition(current));
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    window.addEventListener(OPEN_SETTINGS_EVENT, handleOpen);
    window.addEventListener("resize", handleResize);
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener(OPEN_SETTINGS_EVENT, handleOpen);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("keydown", handleEscape);
    };
  }, []);

  function chooseSection(nextSection: SettingsSection) {
    setSection(nextSection);
    setLoading(true);
    window.localStorage.setItem(SECTION_STORAGE_KEY, nextSection);
  }

  function startDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    dragState.current = {
      pointerId: event.pointerId,
      originX: event.clientX,
      originY: event.clientY,
      startX: position.x,
      startY: position.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function continueDrag(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragState.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    setPosition(
      clampPosition({
        x: drag.startX + event.clientX - drag.originX,
        y: drag.startY + event.clientY - drag.originY,
      }),
    );
  }

  function finishDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (dragState.current?.pointerId !== event.pointerId) return;
    dragState.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setPosition((current) => {
      const next = clampPosition(current);
      window.localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }

  if (!open) return null;

  if (minimized) {
    return (
      <div className="settings-window-minimized" role="status">
        <button onClick={() => setMinimized(false)} type="button">
          <Icon name="settings" size={15} />
          <span>Settings · {activeItem.label}</span>
        </button>
        <button aria-label="Close settings" onClick={() => setOpen(false)} type="button">
          <Icon name="close" size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="settings-window-layer">
      <section
        aria-label="Aster settings"
        className="settings-floating-window"
        role="dialog"
        style={{ left: position.x, top: position.y }}
      >
        <header className="settings-window-titlebar">
          <div
            className="settings-window-drag-handle"
            onPointerCancel={finishDrag}
            onPointerDown={startDrag}
            onPointerMove={continueDrag}
            onPointerUp={finishDrag}
          >
            <Icon name="settings" size={15} />
            <div>
              <strong>Settings</strong>
              <span>{activeItem.label}</span>
            </div>
          </div>
          <div className="settings-window-controls">
            <a href={activeItem.href} title="Open as a full page">
              Open page
            </a>
            <button
              aria-label="Minimize settings"
              onClick={() => setMinimized(true)}
              title="Minimize"
              type="button"
            >
              <span aria-hidden="true">−</span>
            </button>
            <button
              aria-label="Close settings"
              onClick={() => setOpen(false)}
              title="Close"
              type="button"
            >
              <Icon name="close" size={15} />
            </button>
          </div>
        </header>

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
                      aria-current={section === item.key ? "page" : undefined}
                      className={section === item.key ? "active" : ""}
                      key={item.key}
                      onClick={() => chooseSection(item.key)}
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

          <div className="settings-window-content">
            {loading ? (
              <div className="settings-window-loading">Loading {activeItem.label}…</div>
            ) : null}
            <iframe
              key={section}
              onLoad={() => setLoading(false)}
              src={`${activeItem.href}?embedded=1`}
              title={`${activeItem.label} settings`}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
