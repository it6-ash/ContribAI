import { Check } from "@phosphor-icons/react/dist/ssr";
import type { MatchedSkill, SkillGap as Gap } from "@/lib/types";

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

      <div className="grid gap-6 sm:grid-cols-2">
        <section>
          <h3 className="mb-3 text-[13.5px] font-semibold">
            You already have ({matched.length})
          </h3>
          <ul className="space-y-1.5">
            {matched.map((m) => (
              <li key={m.skill} className="flex items-center gap-2 text-[13.5px]">
                <Check size={13} className="shrink-0 text-ok" />
                <span>{m.skill}</span>
                <span className="font-mono text-[11px] text-muted">
                  {Math.round(m.confidence * 100)}%
                </span>
              </li>
            ))}
            {matched.length === 0 ? (
              <li className="text-[13.5px] text-muted">
                None of the required skills appear in your GitHub evidence yet.
              </li>
            ) : null}
          </ul>
        </section>

        <section>
          <h3 className="mb-3 text-[13.5px] font-semibold">Missing ({gaps.length})</h3>
          <ul className="space-y-2.5">
            {gaps.map((g) => (
              <li key={g.skill}>
                <div className="flex items-center gap-2 text-[13.5px]">
                  <span className={g.severity === "core" ? "text-hard" : "text-warn"}>
                    △
                  </span>
                  <span>{g.skill}</span>
                  <span className="font-mono text-[11px] text-muted">
                    {g.severity}
                  </span>
                </div>
                <p className="pl-5 text-[12.5px] text-muted">
                  roughly {Math.round(g.learning_hours)}h to a working level, not mastery
                </p>
              </li>
            ))}
            {gaps.length === 0 ? (
              <li className="text-[13.5px] text-muted">
                No missing skills detected for this issue.
              </li>
            ) : null}
          </ul>
        </section>
      </div>
    </div>
  );
}
