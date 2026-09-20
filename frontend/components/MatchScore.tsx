import type { Recommendation } from "@/lib/types";
import { Bar } from "./primitives";
import { Meter } from "./viz";

const DIMENSION_LABEL: Record<string, string> = {
  skill_match: "Skill match",
  difficulty_match: "Difficulty fit",
  technology_match: "Technology match",
  repository_accessibility: "Repo accessibility",
  issue_clarity: "Issue clarity",
  effort_fit: "Effort fit",
  learning_value: "Learning value",
  repository_activity: "Repo activity",
};

const READINESS_LABEL: Record<string, string> = {
  skills: "Skills",
  repository_familiarity: "Repository familiarity",
  difficulty_fit: "Difficulty fit",
  testing_readiness: "Testing readiness",
  setup_readiness: "Setup readiness",
};

export function MatchScore({ rec }: { rec: Recommendation }) {
  const dimensions = Object.keys(DIMENSION_LABEL).filter(
    (k) => rec.dimensions[k] !== undefined,
  );

  return (
    <div className="space-y-2">
      {dimensions.map((key) => (
        <Bar key={key} label={DIMENSION_LABEL[key]} value={rec.dimensions[key]} />
      ))}
      {rec.dimensions.semantic_similarity !== undefined ? (
        <p className="pt-2 font-mono text-[11px] text-muted">
          Text similarity {rec.dimensions.semantic_similarity.toFixed(3)} breaks ties
          only. It contributes at most 10% of the final score.
        </p>
      ) : null}
    </div>
  );
}

export function ReadinessPanel({ rec }: { rec: Recommendation }) {
  const overall = rec.readiness.overall ?? 0;
  const keys = Object.keys(READINESS_LABEL).filter(
    (k) => rec.readiness[k] !== undefined,
  );

  return (
    <div>
      <div className="mb-4 flex items-end gap-3">
        <span className="font-mono text-[40px] leading-none tracking-tight">
          {Math.round(overall * 100)}
          <span className="text-[18px] text-muted">%</span>
        </span>
        <span className="pb-1 text-[13px] text-muted">
          contribution readiness
        </span>
      </div>
      <div className="viz space-y-3">
        {keys.map((key) => (
          <Meter key={key} label={READINESS_LABEL[key]} value={rec.readiness[key]} />
        ))}
      </div>
      <p className="mt-4 text-[13px] leading-relaxed text-muted">
        {rec.skill_gap_narrative}
      </p>
    </div>
  );
}
