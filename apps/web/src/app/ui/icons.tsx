import {
  ArrowUp,
  Blocks,
  BrainCircuit,
  Check,
  ChevronRight,
  Copy,
  Download,
  Image,
  LockKeyhole,
  Menu,
  MessageSquareText,
  MoreHorizontal,
  PencilLine,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
  Square,
  SquarePen,
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
  | "copy"
  | "download"
  | "edit"
  | "images"
  | "lock"
  | "memory"
  | "menu"
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
  copy: Copy,
  download: Download,
  edit: PencilLine,
  images: Image,
  lock: LockKeyhole,
  memory: BrainCircuit,
  menu: Menu,
  models: Blocks,
  more: MoreHorizontal,
  "new-chat": SquarePen,
  persona: Sparkles,
  refresh: RefreshCw,
  search: Search,
  settings: SlidersHorizontal,
  stop: Square,
  tools: Wrench,
  trash: Trash2,
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
    <span className="aster-mark" style={{ height: size, width: size }} aria-hidden="true">
      <svg fill="none" viewBox="0 0 24 24">
        <path d="M12 3.5v17M4.65 7.75l14.7 8.5M4.65 16.25l14.7-8.5" />
        <circle cx="12" cy="12" fill="currentColor" r="2.15" stroke="none" />
      </svg>
    </span>
  );
}
