"use client";

import type { Difficulty, QualityTier, Recommendation } from "@/lib/types";

export type SortKey = "fit" | "effort" | "readiness" | "difficulty" | "quality";

export interface Filters {
  difficulty: Set<Difficulty>;
  repos: Set<string>;
  /** GitHub labels, straight off the issue. */
  tags: Set<string>;
  /** How well the repository supports newcomers. */
  tiers: Set<QualityTier>;
  hideGaps: boolean;
  sort: SortKey;
}

export const EMPTY_FILTERS: Filters = {
  difficulty: new Set<Difficulty>(),
  repos: new Set<string>(),
  tags: new Set<string>(),
  tiers: new Set<QualityTier>(),
  hideGaps: false,
  sort: "fit",
};

const DIFFICULTIES: Difficulty[] = ["beginner", "intermediate", "advanced"];
// Ascending, so the chips read as a scale rather than an arbitrary list.
const TIERS: QualityTier[] = ["bare", "sparse", "workable", "welcoming", "exemplary"];

const SORTS: Array<[SortKey, string]> = [
  ["fit", "Best fit"],
  ["readiness", "Most ready"],
  ["effort", "Quickest"],
  ["difficulty", "Hardest"],
  ["quality", "Best run projects"],
];

export function applyFilters(recs: Recommendation[], f: Filters): Recommendation[] {
  const out = recs.filter((r) => {
    const d = r.issue.analysis?.difficulty;
    if (f.difficulty.size && (!d || !f.difficulty.has(d))) return false;
    if (f.repos.size && !f.repos.has(r.issue.repository.full_name)) return false;
    if (f.tags.size && !r.issue.labels.some((l) => f.tags.has(l))) return false;
    if (f.tiers.size && !f.tiers.has(r.issue.repository.health.tier)) return false;
    if (f.hideGaps && r.skill_gaps.some((g) => g.severity === "core")) return false;
    return true;
  });

  const rank: Record<Difficulty, number> = { beginner: 0, intermediate: 1, advanced: 2 };
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
      case "quality":
        return (
          b.issue.repository.health.score - a.issue.repository.health.score
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
  const counts = (d: Difficulty) =>
    recs.filter((r) => r.issue.analysis?.difficulty === d).length;
  const tierCount = (t: QualityTier) =>
    recs.filter((r) => r.issue.repository.health.tier === t).length;

  // Only labels that actually appear, most common first: the full GitHub label
  // space is unbounded and most of it would never match anything on screen.
  const tags = [...recs.flatMap((r) => r.issue.labels)]
    .reduce((m, l) => m.set(l, (m.get(l) ?? 0) + 1), new Map<string, number>());
  const topTags = [...tags.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);

  const toggle = <T,>(set: Set<T>, value: T) => {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    return next;
  };

  const dirty =
    filters.difficulty.size > 0 ||
    filters.repos.size > 0 ||
    filters.tags.size > 0 ||
    filters.tiers.size > 0 ||
    filters.hideGaps;

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

      {topTags.length ? (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="mr-1 font-mono text-[10.5px] uppercase tracking-[0.12em] text-muted">
            Tag
          </span>
          {topTags.map(([tag, n]) => (
            <Toggle
              key={tag}
              on={filters.tags.has(tag)}
              onClick={() => onChange({ ...filters, tags: toggle(filters.tags, tag) })}
            >
              {tag} <span className="opacity-60">{n}</span>
            </Toggle>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-1.5">
        <span
          className="mr-1 font-mono text-[10.5px] uppercase tracking-[0.12em] text-muted"
          title="How well the repository supports incoming contributors. Not a judgement of the code."
        >
          Project
        </span>
        {TIERS.filter((t) => tierCount(t) > 0).map((t) => (
          <Toggle
            key={t}
            on={filters.tiers.has(t)}
            onClick={() => onChange({ ...filters, tiers: toggle(filters.tiers, t) })}
          >
            {t} <span className="opacity-60">{tierCount(t)}</span>
          </Toggle>
        ))}
      </div>

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
