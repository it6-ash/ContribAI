import type { MatchedSkill, SkillGap as Gap } from "@/lib/types";
import { SkillDumbbell } from "./viz";

export function SkillGapPanel({
  matched,
  gaps,
  narrative,
}: {
  matched: MatchedSkill[];
  gaps: Gap[];
  narrative: string;
}) {
  return (
    <div className="space-y-6">
      <p className="max-w-[68ch] text-[14px] leading-relaxed">{narrative}</p>

      {/* One row per required skill, showing the distance between your
          evidence and what this issue needs. Two tick-lists made the reader
          diff them by eye; a dumbbell puts the gap on one axis. */}
      <SkillDumbbell
        rows={[
          ...matched.map((m) => ({
            skill: m.skill,
            have: m.confidence,
            // A skill you already demonstrate is treated as met at your own level.
            needed: Math.min(m.confidence, 0.6),
          })),
          ...gaps.map((g) => ({
            skill: g.skill,
            have: 0,
            needed: g.severity === "core" ? 0.7 : 0.45,
            severity: g.severity,
          })),
        ]}
      />
    </div>
  );
}
