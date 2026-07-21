import {
  ArchiveX,
  ArrowUp,
  Blocks,
  BrainCircuit,
  Check,
  ChevronRight,
  Copy,
  Download,
  Folder,
  Hash,
  Image,
  Inbox,
  LockKeyhole,
  Mail,
  Maximize2,
  Menu,
  MessageCircleMore,
  MessageSquareText,
  Minimize2,
  MoreHorizontal,
  PanelLeft,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRight,
  PencilLine,
  RefreshCw,
  Reply,
  Search,
  Send,
  ShieldX,
  SlidersHorizontal,
  Sparkles,
  Square,
  SquarePen,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  Upload,
  UserRound,
  Wrench,
  X,
  type LucideIcon,
  type LucideProps,
} from "lucide-react";

export type IconName =
  | "account"
  | "arrow-up"
  | "chat"
  | "check"
  | "chevron-right"
  | "close"
  | "collapse-panel"
  | "copy"
  | "discord"
  | "dock-left"
  | "dock-right"
  | "download"
  | "edit"
  | "email"
  | "expand-panel"
  | "focus"
  | "folder"
  | "hash"
  | "images"
  | "inbox"
  | "junk"
  | "lock"
  | "memory"
  | "menu"
  | "models"
  | "more"
  | "negative"
  | "new-chat"
  | "persona"
  | "positive"
  | "refresh"
  | "reply"
  | "search"
  | "sent"
  | "settings"
  | "skills"
  | "spam"
  | "stop"
  | "tools"
  | "trash"
  | "unfocus"
  | "upload";

type IconProps = Omit<LucideProps, "children" | "size"> & {
  name: IconName;
  size?: number;
};

const ICONS: Record<IconName, LucideIcon> = {
  account: UserRound,
  "arrow-up": ArrowUp,
  chat: MessageSquareText,
  check: Check,
  "chevron-right": ChevronRight,
  close: X,
  "collapse-panel": PanelLeftClose,
  copy: Copy,
  discord: MessageCircleMore,
  "dock-left": PanelLeft,
  "dock-right": PanelRight,
  download: Download,
  edit: PencilLine,
  email: Mail,
  "expand-panel": PanelLeftOpen,
  focus: Maximize2,
  folder: Folder,
  hash: Hash,
  images: Image,
  inbox: Inbox,
  junk: ArchiveX,
  lock: LockKeyhole,
  memory: BrainCircuit,
  menu: Menu,
  models: Blocks,
  more: MoreHorizontal,
  negative: ThumbsDown,
  "new-chat": SquarePen,
  persona: Sparkles,
  positive: ThumbsUp,
  refresh: RefreshCw,
  reply: Reply,
  search: Search,
  sent: Send,
  settings: SlidersHorizontal,
  skills: Sparkles,
  spam: ShieldX,
  stop: Square,
  tools: Wrench,
  trash: Trash2,
  unfocus: Minimize2,
  upload: Upload,
};

export function Icon({ name, size = 16, strokeWidth = 1.75, ...props }: IconProps) {
  const Glyph = ICONS[name];

  return (
    <Glyph
      aria-hidden="true"
      size={size}
      strokeWidth={strokeWidth}
      {...props}
    />
  );
}

export function AsterMark({ size = 24 }: { size?: number }) {
  return (
    <span
      aria-hidden="true"
      className="aster-mark"
      style={{
        background:
          "radial-gradient(circle at 50% 46%, rgba(112, 122, 231, 0.15), transparent 44%), linear-gradient(145deg, #12151b, #080a0e)",
        borderColor: "rgba(240, 242, 248, 0.12)",
        boxShadow:
          "inset 0 1px rgba(255, 255, 255, 0.055), 0 5px 16px rgba(0, 0, 0, 0.22)",
        height: size,
        overflow: "hidden",
        width: size,
      }}
    >
      <svg
        fill="none"
        style={{ height: "76%", overflow: "visible", stroke: "none", width: "76%" }}
        viewBox="290 270 674 660"
      >
        <defs>
          <linearGradient id="aster-mark-silver" x1="390" x2="865" y1="310" y2="900">
            <stop offset="0" stopColor="#ffffff" />
            <stop offset="0.52" stopColor="#eef0f6" />
            <stop offset="1" stopColor="#cfd3df" />
          </linearGradient>
          <linearGradient id="aster-mark-core" x1="582" x2="675" y1="700" y2="874">
            <stop offset="0" stopColor="#f3f1ff" />
            <stop offset="0.48" stopColor="#c9c8ff" />
            <stop offset="1" stopColor="#8f97ff" />
          </linearGradient>
          <filter id="aster-mark-glow" height="160%" width="180%" x="-40%" y="-30%">
            <feGaussianBlur result="blur" stdDeviation="9" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path d="M606 305 402 635h111l93-152V305Z" fill="url(#aster-mark-silver)" />
        <path d="M648 304v178l91 151 113 2-204-331Z" fill="url(#aster-mark-silver)" />
        <path
          d="m379 678-55 92 76 124 183 2-58-94H415l73-124H379Z"
          fill="url(#aster-mark-silver)"
        />
        <path
          d="M875 678H766l73 123-111 1-57 94 182-1 77-126-55-91Z"
          fill="url(#aster-mark-silver)"
        />
        <path
          d="m627 681-63 103 63 103 62-102-62-104Z"
          fill="url(#aster-mark-core)"
          filter="url(#aster-mark-glow)"
        />
      </svg>
    </span>
  );
}
