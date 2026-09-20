"use client";

import type { Level, Recommendation } from "@/lib/types";

export type SortKey = "fit" | "effort" | "readiness" | "difficulty";

export interface Filters {
  difficulty: Set<Level>;
  repos: Set<string>;
  hideGaps: boolean;
  sort: SortKey;
}

export const EMPTY_FILTERS: Filters = {
  difficulty: new Set<Level>(),
  repos: new Set<string>(),
  hideGaps: false,
  sort: "fit",
};

const DIFFICULTIES: Level[] = ["beginner", "intermediate", "advanced"];

const SORTS: Array<[SortKey, string]> = [
  ["fit", "Best fit"],
  ["readiness", "Most ready"],
  ["effort", "Quickest"],
  ["difficulty", "Hardest"],
];

export function applyFilters(recs: Recommendation[], f: Filters): Recommendation[] {
  const out = recs.filter((r) => {
    const d = r.issue.analysis?.difficulty;
    if (f.difficulty.size && (!d || !f.difficulty.has(d))) return false;
    if (f.repos.size && !f.repos.has(r.issue.repository.full_name)) return false;
    if (f.hideGaps && r.skill_gaps.some((g) => g.severity === "core")) return false;
    return true;
  });

  const rank: Record<Level, number> = { beginner: 0, intermediate: 1, advanced: 2 };
  return out.sort((a, b) => {
    switch (f.sort) {
      case "readiness":
        return (b.readiness.overall ?? 0) - (a.readiness.overall ?? 0);
      case "effort":
        return (
          (a.issue.analysis?.estimated_hours_min ?? 99) -
          (b.issue.analysis?.estimated_hours_min ?? 99)
        );
      case "difficulty":
        return (
          rank[b.issue.analysis?.difficulty ?? "intermediate"] -
          rank[a.issue.analysis?.difficulty ?? "intermediate"]
        );
      default:
        return b.fit_score - a.fit_score;
    }
  });
}

function Toggle({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={on}
      className={`rounded-full border px-2.5 py-1 font-mono text-[11.5px] transition-colors ${
        on
          ? "border-accent/50 bg-accent/10 text-accent"
          : "border-line text-muted hover:border-muted/50 hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}

/** Filters live in one row above the results, and every control is instant:
 *  the whole corpus is already in memory, so nothing here needs a round trip. */
export function DashboardControls({
  recs,
  filters,
  onChange,
  shown,
}: {
  recs: Recommendation[];
  filters: Filters;
  onChange: (f: Filters) => void;
  shown: number;
}) {
  const repos = [...new Set(recs.map((r) => r.issue.repository.full_name))];
  const counts = (d: Level) =>
    recs.filter((r) => r.issue.analysis?.difficulty === d).length;

  const toggle = <T,>(set: Set<T>, value: T) => {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    return next;
  };

  const dirty =
    filters.difficulty.size > 0 || filters.repos.size > 0 || filters.hideGaps;

  return (
    <div className="panel flex flex-wrap items-center gap-x-5 gap-y-3 px-4 py-3">
      <div className="flex items-center gap-1.5">
        <span className="mr-1 font-mono text-[10.5px] uppercase tracking-[0.12em] text-muted">
          Level
        </span>
        {DIFFICULTIES.filter((d) => counts(d) > 0).map((d) => (
          <Toggle
            key={d}
            on={filters.difficulty.has(d)}
            onClick={() =>
              onChange({ ...filters, difficulty: toggle(filters.difficulty, d) })
            }
          >
            {d} <span className="opacity-60">{counts(d)}</span>
          </Toggle>
        ))}
      </div>

      {repos.length > 1 ? (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="mr-1 font-mono text-[10.5px] uppercase tracking-[0.12em] text-muted">
            Repo
          </span>
          {repos.slice(0, 5).map((name) => (
            <Toggle
              key={name}
              on={filters.repos.has(name)}
              onClick={() => onChange({ ...filters, repos: toggle(filters.repos, name) })}
            >
              {name.split("/")[1] ?? name}
            </Toggle>
          ))}
        </div>
      ) : null}

      <Toggle
        on={filters.hideGaps}
        onClick={() => onChange({ ...filters, hideGaps: !filters.hideGaps })}
      >
        ready to start
      </Toggle>

      <div className="ml-auto flex items-center gap-2">
        <label htmlFor="sort" className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-muted">
          Sort
        </label>
        <select
          id="sort"
          value={filters.sort}
          onChange={(e) => onChange({ ...filters, sort: e.target.value as SortKey })}
          className="rounded-[8px] border border-line bg-surface px-2 py-1 text-[12.5px]"
        >
          {SORTS.map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>

        <span className="font-mono text-[11.5px] text-muted">
          {shown}/{recs.length}
        </span>

        {dirty ? (
          <button
            onClick={() => onChange({ ...EMPTY_FILTERS, sort: filters.sort })}
            className="text-[12px] text-accent underline underline-offset-4"
          >
            clear
          </button>
        ) : null}
      </div>
    </div>
  );
}
