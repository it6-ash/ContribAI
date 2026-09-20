import { File, Question, Warning } from "@phosphor-icons/react/dist/ssr";
import { hoursLabel } from "@/lib/api";
import type { IssueAnalysis } from "@/lib/types";
import { Chip, DifficultyBadge, SourceTag } from "./primitives";

export function IssueExplanation({ analysis }: { analysis: IssueAnalysis }) {
  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-center gap-3">
        <DifficultyBadge level={analysis.difficulty} />
        <span className="font-mono text-[12px] text-muted">
          {hoursLabel(analysis.estimated_hours_min, analysis.estimated_hours_max)}
        </span>
        <span className="font-mono text-[12px] text-muted">
          confidence: {analysis.confidence}
        </span>
        <SourceTag source={analysis.source} />
      </header>

      <section>
        <h3 className="mb-2 text-[14px] font-semibold">What is happening</h3>
        <p className="max-w-[68ch] text-[14px] leading-relaxed text-muted">
          {analysis.problem_description}
        </p>
      </section>

      <section>
        <h3 className="mb-2 text-[14px] font-semibold">Why it matters</h3>
        <p className="max-w-[68ch] text-[14px] leading-relaxed text-muted">
          {analysis.why_it_matters}
        </p>
      </section>

      <section>
        <h3 className="mb-2 text-[14px] font-semibold">
          Why this difficulty rating
        </h3>
        <p className="max-w-[68ch] text-[14px] leading-relaxed text-muted">
          {analysis.difficulty_basis}
        </p>
      </section>

      {analysis.affected_files.length ? (
        <section>
          <h3 className="mb-2 text-[14px] font-semibold">Likely affected files</h3>
          <p className="mb-3 text-[12.5px] text-muted">
            Inferred from the issue text against the repository tree. Verify before
            trusting.
          </p>
          <ul className="space-y-1">
            {analysis.affected_files.map((file, i) => (
              <li
                key={file}
                className="flex items-center gap-2 font-mono text-[12.5px]"
              >
                <File size={13} className="shrink-0 text-muted" />
                <span className={i === 0 ? "text-accent" : "text-foreground"}>
                  {file}
                </span>
                {i === 0 ? (
                  <span className="text-[11px] text-muted">named in the issue</span>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {analysis.concepts.length ? (
        <section>
          <h3 className="mb-2 text-[14px] font-semibold">Concepts involved</h3>
          <div className="flex flex-wrap gap-2">
            {analysis.concepts.map((c) => (
              <Chip key={c}>{c}</Chip>
            ))}
          </div>
        </section>
      ) : null}

      {analysis.investigation_order.length ? (
        <section>
          <h3 className="mb-3 text-[14px] font-semibold">Suggested investigation order</h3>
          <ol className="space-y-2">
            {analysis.investigation_order.map((step, i) => (
              <li key={step} className="flex gap-3 text-[14px] leading-relaxed">
                <span className="mt-0.5 font-mono text-[12px] text-muted">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="text-muted">{step}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {analysis.open_questions.length ? (
        <section className="panel-2 p-4">
          <h3 className="mb-2 flex items-center gap-2 text-[14px] font-semibold">
            <Warning size={15} className="text-warn" />
            Verify before you start coding
          </h3>
          <ul className="space-y-1.5">
            {analysis.open_questions.map((q) => (
              <li key={q} className="flex gap-2 text-[13.5px] leading-relaxed text-muted">
                <Question size={14} className="mt-0.5 shrink-0 text-muted" />
                {q}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
