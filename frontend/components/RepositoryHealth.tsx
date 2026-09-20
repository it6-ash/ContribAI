import { Check, Minus } from "@phosphor-icons/react/dist/ssr";
import type { RepoHealth } from "@/lib/types";

const ACTIVITY_COLOR: Record<RepoHealth["activity"], string> = {
  high: "text-ok",
  medium: "text-warn",
  low: "text-hard",
  unknown: "text-muted",
};

/** Factual GitHub signals only. The composite score is labelled a heuristic
 *  because that is what it is, not a verdict on the project. */
export function RepositoryHealth({
  health,
  compact = false,
}: {
  health: RepoHealth;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-muted">
        <span className={ACTIVITY_COLOR[health.activity]}>
          {health.activity} activity
        </span>
        {health.days_since_commit !== null ? (
          <span>last commit {health.days_since_commit}d ago</span>
        ) : null}
        <span>{health.has_contributing ? "CONTRIBUTING.md" : "no contrib guide"}</span>
        <span>{health.has_tests ? "tests" : "no tests found"}</span>
      </div>
    );
  }

  const rows: Array<[string, string, boolean | null]> = [
    [
      "Last commit",
      health.days_since_commit !== null ? `${health.days_since_commit} days ago` : "unknown",
      health.days_since_commit !== null ? health.days_since_commit <= 60 : null,
    ],
    ["Activity", health.activity, health.activity !== "low"],
    ["Contributors", String(health.contributors || "unknown"), health.contributors >= 5],
    [
      "Median PR response",
      health.median_pr_response_hours !== null
        ? `~${Math.round(health.median_pr_response_hours)}h`
        : "unknown",
      health.median_pr_response_hours !== null
        ? health.median_pr_response_hours <= 72
        : null,
    ],
    ["CONTRIBUTING.md", health.has_contributing ? "present" : "missing", health.has_contributing],
    ["Tests", health.has_tests ? "detected" : "not detected", health.has_tests],
    ["License", health.has_license ? "present" : "missing", health.has_license],
    ["Open issues", String(health.open_issues), null],
  ];

  return (
    <div>
      <dl className="grid grid-cols-2 gap-x-6">
        {rows.map(([label, value, good]) => (
          <div
            key={label}
            className="flex items-center justify-between gap-3 border-b border-line py-1.5 last:border-b-0"
          >
            <dt className="text-[13px] text-muted">{label}</dt>
            <dd className="flex items-center gap-1.5 font-mono text-[12px]">
              {good === true ? (
                <Check size={12} className="text-ok" />
              ) : good === false ? (
                <Minus size={12} className="text-hard" />
              ) : null}
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 font-mono text-[11px] text-muted">
        Composite {Math.round(health.score * 100)}/100 is an internal heuristic over the
        signals above, not a rating of the project.
      </p>
    </div>
  );
}
