"use client";

import { useState, type ReactNode } from "react";

/** Five-step sequential ramp, validated against this surface. Index 0 is
 *  nearest zero. Never interpolate between these; the gaps are the point. */
export const SEQ = [
  "var(--seq-1)",
  "var(--seq-2)",
  "var(--seq-3)",
  "var(--seq-4)",
  "var(--seq-5)",
] as const;

/** Map a value onto the ramp across an explicit domain.
 *
 *  The domain is a parameter because scoring dimensions realistically land
 *  between about 0.25 and 1.0: against a 0-1 domain nearly every cell fell in
 *  the two lightest steps and the grid read as one flat colour. The legend
 *  prints the domain so a reader is never guessing what "weak" means. */
export function seqStep(value: number, lo = 0, hi = 1): string {
  if (!Number.isFinite(value) || value <= 0) return "var(--viz-empty)";
  const t = Math.max(0, Math.min(0.999, (value - lo) / (hi - lo)));
  return SEQ[Math.floor(t * SEQ.length)];
}

/** Domain used by the match heatmap; shared so the legend cannot drift. */
export const SCORE_DOMAIN: [number, number] = [0.25, 1];

/** Hover tooltip. Follows the pointer, never covers the mark it describes. */
export function useTooltip() {
  const [tip, setTip] = useState<{ x: number; y: number; body: ReactNode } | null>(
    null,
  );
  const show = (e: React.MouseEvent, body: ReactNode) =>
    setTip({ x: e.clientX, y: e.clientY, body });
  const hide = () => setTip(null);
  const node = tip ? (
    <div
      role="tooltip"
      className="pointer-events-none fixed z-50 max-w-[280px] floating rounded border border-line bg-surface-2 px-3 py-2 text-[12.5px] leading-relaxed"
      style={{
        left: Math.min(tip.x + 14, (globalThis.innerWidth ?? 1400) - 300),
        top: tip.y + 16,
      }}
    >
      {tip.body}
    </div>
  ) : null;
  return { show, hide, node };
}

/** A single ratio against a limit. A meter, not a two-slice pie. */
export function Meter({
  label,
  value,
  hint,
}: {
  label: string;
  value: number;
  hint?: string;
}) {
  const v = Math.max(0, Math.min(1, value));
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[12.5px] text-muted">{label}</span>
        <span className="font-mono text-[12px] tabular-nums">
          {Math.round(v * 100)}%
        </span>
      </div>
      <div
        className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full"
        style={{ background: "var(--viz-empty)" }}
        role="meter"
        aria-valuenow={Math.round(v * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        {/* One colour for every meter, not a ramp keyed to the value.
            Readiness dimensions are nominal (Skills, Testing, Setup have no
            natural order), so shading each by its own magnitude would encode
            bar length twice and spend the only free channel on nothing. */}
        <div
          className="bar-fill h-full"
          style={{
            width: `${v * 100}%`,
            background: "var(--seq-3)",
            borderRadius: "0 4px 4px 0",
          }}
        />
      </div>
      {hint ? <p className="mt-1 text-[11.5px] text-muted/80">{hint}</p> : null}
    </div>
  );
}

/** Dumbbell: what you have vs what the issue needs, per skill.
 *  One hue in two shades, because this is before/after on one measure, not
 *  two competing series. */
export function SkillDumbbell({
  rows,
}: {
  rows: Array<{ skill: string; have: number; needed: number; severity?: string }>;
}) {
  const { show, hide, node } = useTooltip();
  if (!rows.length) return null;

  return (
    <div className="viz">
      <div className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[11.5px] text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rounded-full" style={{ background: "var(--seq-5)" }} />
          your evidence
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rounded-full" style={{ background: "var(--seq-2)" }} />
          needed for this issue
        </span>
      </div>

      <div className="space-y-0">
        {rows.map((r) => {
          const gap = r.needed - r.have;
          const lo = Math.min(r.have, r.needed);
          const hi = Math.max(r.have, r.needed);
          return (
            <div
              key={r.skill}
              className="grid grid-cols-[110px_1fr_46px] items-center gap-3 border-b border-line py-2.5 last:border-b-0"
              onMouseMove={(e) =>
                show(
                  e,
                  <>
                    <p className="font-medium">{r.skill}</p>
                    <p className="text-muted">
                      you {Math.round(r.have * 100)}% · needed{" "}
                      {Math.round(r.needed * 100)}%
                    </p>
                    <p className="mt-1 text-muted">
                      {gap <= 0.02
                        ? "No gap. Your GitHub evidence covers this."
                        : `Gap of ${Math.round(gap * 100)} points${
                            r.severity === "core" ? ", and it is a core technology" : ""
                          }.`}
                    </p>
                  </>,
                )
              }
              onMouseLeave={hide}
            >
              <span className="truncate text-[13px]">{r.skill}</span>

              <svg viewBox="0 0 100 12" className="h-3 w-full overflow-visible">
                <line
                  x1="0"
                  y1="6"
                  x2="100"
                  y2="6"
                  stroke="var(--viz-grid)"
                  strokeWidth="1"
                />
                {/* 2px connector between the two ends */}
                <line
                  x1={lo * 100}
                  y1="6"
                  x2={hi * 100}
                  y2="6"
                  stroke={gap > 0.02 ? "var(--seq-2)" : "var(--seq-4)"}
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                {/* Each end carries a 2px ring in the surface colour. */}
                <circle
                  cx={r.needed * 100}
                  cy="6"
                  r="4"
                  fill="var(--seq-2)"
                  stroke="var(--surface)"
                  strokeWidth="2"
                />
                <circle
                  cx={r.have * 100}
                  cy="6"
                  r="4"
                  fill="var(--seq-5)"
                  stroke="var(--surface)"
                  strokeWidth="2"
                />
              </svg>

              <span
                className={`text-right font-mono text-[11.5px] tabular-nums ${
                  gap > 0.02 ? "text-warn" : "text-muted"
                }`}
              >
                {gap > 0.02 ? `-${Math.round(gap * 100)}` : "ok"}
              </span>
            </div>
          );
        })}
      </div>
      {node}
    </div>
  );
}

/** Where the corpus went. Part-to-whole, so a stacked bar, not a funnel cone. */
export function FilterFunnel({
  analyzed,
  passed,
  strong,
  dropped,
}: {
  analyzed: number;
  passed: number;
  strong: number;
  dropped: Record<string, number>;
}) {
  const { show, hide, node } = useTooltip();
  if (!analyzed) return null;

  const reasons = Object.entries(dropped).sort((a, b) => b[1] - a[1]);
  const segments = [
    { label: "strong match", n: strong, fill: "var(--seq-5)" },
    { label: "passed filters", n: Math.max(0, passed - strong), fill: "var(--seq-3)" },
    ...reasons.map(([label, n]) => ({ label, n, fill: "var(--viz-empty)" })),
  ].filter((s) => s.n > 0);

  return (
    <div className="viz">
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="text-[13.5px] leading-relaxed">
          We looked at <strong className="font-semibold">{analyzed}</strong> open issues,
          ruled out <strong className="font-semibold">{analyzed - passed}</strong>, and
          found <strong className="font-semibold text-accent">{strong}</strong> that are
          a strong fit for you.
        </h3>
      </div>

      {/* 2px surface gaps do the separating between segments, not borders. */}
      <div className="mt-3 flex h-3 w-full gap-[2px] overflow-hidden rounded-[4px]">
        {segments.map((s) => (
          <div
            key={s.label}
            className="h-full cursor-default transition-opacity hover:opacity-80"
            style={{ width: `${(s.n / analyzed) * 100}%`, background: s.fill }}
            onMouseMove={(e) =>
              show(
                e,
                <>
                  <p className="font-medium">{s.label}</p>
                  <p className="text-muted">
                    {s.n} of {analyzed} issues ({Math.round((s.n / analyzed) * 100)}%)
                  </p>
                </>,
              )
            }
            onMouseLeave={hide}
          />
        ))}
      </div>

      {reasons.length ? (
        <p className="mt-2.5 font-mono text-[11px] leading-relaxed text-muted">
          filtered: {reasons.map(([r, n]) => `${n} ${r}`).join(" · ")}
        </p>
      ) : null}
      {node}
    </div>
  );
}
