import type { ReactNode } from "react";
import type { Difficulty } from "@/lib/types";

const DIFFICULTY_STYLE: Record<Difficulty, string> = {
  beginner: "text-ok border-ok/30 bg-ok/10",
  intermediate: "text-warn border-warn/30 bg-warn/10",
  advanced: "text-hard border-hard/30 bg-hard/10",
};

export function DifficultyBadge({ level }: { level: Difficulty }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[11px] tracking-tight ${DIFFICULTY_STYLE[level]}`}
    >
      {level}
    </span>
  );
}

export function Chip({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "accent";
}) {
  const style =
    tone === "accent"
      ? "border-accent/35 bg-accent/10 text-accent"
      : "border-line bg-surface-2 text-muted";
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[11px] ${style}`}
    >
      {children}
    </span>
  );
}

/** Deterministic vs inferred is a product-level distinction, so it gets a
 *  visible marker rather than a footnote nobody reads. */
export function SourceTag({ source }: { source: "heuristic" | "llm" | string }) {
  return (
    <span
      className="font-mono text-[10.5px] text-muted"
      title={
        source === "llm"
          ? "Written by the language model from the GitHub data below"
          : "Derived deterministically from GitHub data, no model involved"
      }
    >
      {source === "llm" ? "ai-written" : "rule-derived"}
    </span>
  );
}

export function Bar({
  value,
  label,
  showValue = true,
}: {
  value: number;
  label?: string;
  showValue?: boolean;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div className="flex items-center gap-3">
      {label ? (
        <span className="w-40 shrink-0 text-[13px] text-muted">{label}</span>
      ) : null}
      <div
        className="h-1 flex-1 overflow-hidden rounded-full bg-line"
        role="meter"
        aria-valuenow={Math.round(clamped * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? "score"}
      >
        <div
          className="bar-fill h-full rounded-full bg-accent"
          style={{ width: `${clamped * 100}%` }}
        />
      </div>
      {showValue ? (
        <span className="w-10 shrink-0 text-right font-mono text-[12px] text-muted">
          {Math.round(clamped * 100)}%
        </span>
      ) : null}
    </div>
  );
}

export function Button({
  children,
  onClick,
  href,
  variant = "primary",
  disabled,
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  variant?: "primary" | "ghost";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  const base =
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[10px] px-4 py-2 text-[14px] font-medium transition-[transform,background-color,border-color] active:translate-y-px disabled:pointer-events-none disabled:opacity-45";
  // Near-black label on the blue accent clears WCAG AA comfortably.
  const style =
    variant === "primary"
      ? "bg-accent text-on-accent hover:bg-accent/90"
      : "border border-line bg-surface text-foreground hover:border-muted/50";
  const cls = `${base} ${style} ${className}`;

  if (href) {
    return (
      <a href={href} className={cls}>
        {children}
      </a>
    );
  }
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={cls}>
      {children}
    </button>
  );
}

export function SectionTitle({
  children,
  right,
}: {
  children: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-baseline justify-between gap-4">
      <h2 className="text-[15px] font-semibold tracking-tight">{children}</h2>
      {right}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-line ${className}`}
      aria-hidden="true"
    />
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="panel flex flex-col items-start gap-3 p-8">
      <h3 className="text-[15px] font-semibold">{title}</h3>
      <p className="max-w-[60ch] text-[14px] leading-relaxed text-muted">{body}</p>
      {action}
    </div>
  );
}

export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="rounded-[10px] border border-hard/40 bg-hard/10 p-4">
      <p className="text-[14px] text-foreground">{message}</p>
      {retry ? (
        <button
          onClick={retry}
          className="mt-3 text-[13px] text-accent underline underline-offset-4"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
