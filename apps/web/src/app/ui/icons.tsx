import type { SVGProps } from "react";

export type IconName =
  | "account"
  | "arrow-up"
  | "chat"
  | "check"
  | "chevron-right"
  | "close"
  | "copy"
  | "download"
  | "edit"
  | "lock"
  | "models"
  | "more"
  | "new-chat"
  | "persona"
  | "refresh"
  | "search"
  | "settings"
  | "stop"
  | "tools"
  | "trash"
  | "upload";

type IconProps = Omit<SVGProps<SVGSVGElement>, "children"> & {
  name: IconName;
  size?: number;
};

export function Icon({ name, size = 16, ...props }: IconProps) {
  const paths: Record<IconName, React.ReactNode> = {
    account: (
      <>
        <circle cx="12" cy="8" r="3.25" />
        <path d="M5.5 19c.8-3.4 3-5.1 6.5-5.1s5.7 1.7 6.5 5.1" />
      </>
    ),
    "arrow-up": (
      <>
        <path d="m6.5 10.5 5.5-5 5.5 5" />
        <path d="M12 6v12.5" />
      </>
    ),
    chat: (
      <>
        <path d="M5 5.5h14v10H9l-4 3v-13Z" />
        <path d="M8.5 9h7M8.5 12h4.5" />
      </>
    ),
    check: <path d="m5 12.5 4.2 4.2L19 7" />,
    "chevron-right": <path d="m9 6 6 6-6 6" />,
    close: <path d="m7 7 10 10M17 7 7 17" />,
    copy: (
      <>
        <rect x="8" y="8" width="11" height="11" rx="2" />
        <path d="M16 8V5H5v11h3" />
      </>
    ),
    download: (
      <>
        <path d="M12 4v11" />
        <path d="m8 11 4 4 4-4M5 20h14" />
      </>
    ),
    edit: (
      <>
        <path d="m14.5 5.5 4 4L9 19H5v-4l9.5-9.5Z" />
        <path d="m12.5 7.5 4 4" />
      </>
    ),
    lock: (
      <>
        <rect x="5" y="10" width="14" height="10" rx="2" />
        <path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10" />
      </>
    ),
    models: (
      <>
        <rect x="4" y="5" width="16" height="4" rx="1.5" />
        <rect x="4" y="10" width="16" height="4" rx="1.5" />
        <rect x="4" y="15" width="16" height="4" rx="1.5" />
        <path d="M8 7h.01M8 12h.01M8 17h.01" />
      </>
    ),
    more: (
      <>
        <circle cx="6" cy="12" r="1" fill="currentColor" stroke="none" />
        <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
        <circle cx="18" cy="12" r="1" fill="currentColor" stroke="none" />
      </>
    ),
    "new-chat": (
      <>
        <path d="M6 18.5V7a2 2 0 0 1 2-2h7" />
        <path d="M13 5h6v6" />
        <path d="m12 12 7-7" />
        <path d="M18 14v4a2 2 0 0 1-2 2H8" />
      </>
    ),
    persona: (
      <>
        <path d="M12 3.5 14 8l4.5 2-4.5 2-2 4.5-2-4.5-4.5-2L10 8l2-4.5Z" />
        <path d="m18.5 15 .8 1.8 1.7.7-1.7.8-.8 1.7-.8-1.7-1.7-.8 1.7-.7.8-1.8Z" />
      </>
    ),
    refresh: (
      <>
        <path d="M18.5 8A7 7 0 1 0 19 15" />
        <path d="M18.5 4.5V8h-3.5" />
      </>
    ),
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="5.5" />
        <path d="m15 15 4 4" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M6 6l1.4 1.4M16.6 16.6 18 18M18 6l-1.4 1.4M7.4 16.6 6 18" />
      </>
    ),
    stop: <rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" stroke="none" />,
    tools: (
      <>
        <path d="M14.5 5.5a4 4 0 0 0-5.2 5.2L4.5 15.5a2.1 2.1 0 0 0 3 3l4.8-4.8a4 4 0 0 0 5.2-5.2l-2.4 2.4-2-2 2.4-2.4Z" />
        <path d="m6.7 16.3 1 1" />
      </>
    ),
    trash: (
      <>
        <path d="M5 7h14" />
        <path d="m9 7 .5-2h5l.5 2M7 7l1 13h8l1-13" />
        <path d="M10 10v6M14 10v6" />
      </>
    ),
    upload: (
      <>
        <path d="M12 20V9" />
        <path d="m8 13 4-4 4 4M5 4h14" />
      </>
    ),
  };

  return (
    <svg
      aria-hidden="true"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      {...props}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.65"
    >
      {paths[name]}
    </svg>
  );
}

export function AsterMark({ size = 24 }: { size?: number }) {
  return (
    <span className="aster-mark" style={{ height: size, width: size }} aria-hidden="true">
      <svg fill="none" viewBox="0 0 24 24">
        <path d="M12 4v16M5.1 8l13.8 8M5.1 16l13.8-8" />
      </svg>
    </span>
  );
}
