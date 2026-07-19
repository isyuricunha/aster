import { useId } from "react";
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
  const instanceId = useId().replace(/:/g, "");
  const silverGradientId = `aster-silver-${instanceId}`;
  const coreGradientId = `aster-core-${instanceId}`;
  const glowId = `aster-glow-${instanceId}`;

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
          <linearGradient id={silverGradientId} x1="390" x2="865" y1="310" y2="900">
            <stop offset="0" stopColor="#ffffff" />
            <stop offset="0.52" stopColor="#eef0f6" />
            <stop offset="1" stopColor="#cfd3df" />
          </linearGradient>
          <linearGradient id={coreGradientId} x1="582" x2="675" y1="700" y2="874">
            <stop offset="0" stopColor="#f3f1ff" />
            <stop offset="0.48" stopColor="#c9c8ff" />
            <stop offset="1" stopColor="#8f97ff" />
          </linearGradient>
          <filter id={glowId} height="160%" width="180%" x="-40%" y="-30%">
            <feGaussianBlur result="blur" stdDeviation="9" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path d="M606 305 402 635h111l93-152V305Z" fill={`url(#${silverGradientId})`} />
        <path d="M648 304v178l91 151 113 2-204-331Z" fill={`url(#${silverGradientId})`} />
        <path
          d="m379 678-55 92 76 124 183 2-58-94H415l73-124H379Z"
          fill={`url(#${silverGradientId})`}
        />
        <path
          d="M875 678H766l73 123-111 1-57 94 182-1 77-126-55-91Z"
          fill={`url(#${silverGradientId})`}
        />
        <path
          d="m627 681-63 103 63 103 62-102-62-104Z"
          fill={`url(#${coreGradientId})`}
          filter={`url(#${glowId})`}
        />
      </svg>
    </span>
  );
}
