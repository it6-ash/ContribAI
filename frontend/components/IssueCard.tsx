"use client";

import Link from "next/link";
import { ArrowRight, Clock, GitBranch } from "@phosphor-icons/react/dist/ssr";
import { hoursLabel } from "@/lib/api";
import type { Recommendation } from "@/lib/types";
import { Button, Chip, DifficultyBadge } from "./primitives";
import { RepositoryHealth } from "./RepositoryHealth";

const BUCKET_LABEL: Record<string, string> = {
  best_fit: "Best fit",
  skill_stretch: "Skill stretch",
  gentle_start: "Gentle start",
  worth_a_look: "Worth a look",
};

export function IssueCard({
  rec,
  index = 0,
}: {
  rec: Recommendation;
  index?: number;
}) {
  const { issue, fit_score, matched_skills, skill_gaps, reasoning } = rec;
  const analysis = issue.analysis;

  return (
    <article
      className="reveal panel p-5 transition-colors hover:border-muted/40"
      style={{ "--i": index } as React.CSSProperties}
    >
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[12px] text-muted">
            <GitBranch size={13} />
            <span className="truncate font-mono">{issue.repository.full_name}</span>
            <span className="font-mono text-muted/60">#{issue.number}</span>
            {issue.is_demo ? (
              <span className="shrink-0 rounded border border-warn/35 px-1 py-px font-mono text-[10px] text-warn">
                sample
              </span>
            ) : null}
          </div>
          <h3 className="mt-1.5 text-[16px] font-semibold leading-snug tracking-tight">
            <Link href={`/issues/${issue.id}`} className="hover:text-accent">
              {issue.title}
            </Link>
          </h3>
        </div>

        <div className="shrink-0 text-right">
          <div className="font-mono text-[26px] leading-none tracking-tight text-accent">
            {Math.round(fit_score * 100)}
            <span className="text-[14px] text-muted">%</span>
          </div>
          <div className="mt-1 font-mono text-[10.5px] uppercase tracking-[0.12em] text-muted">
            {BUCKET_LABEL[rec.bucket] ?? "match"}
          </div>
        </div>
      </div>

      {analysis ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <DifficultyBadge level={analysis.difficulty} />
          <span className="inline-flex items-center gap-1 font-mono text-[11px] text-muted">
            <Clock size={12} />
            {hoursLabel(analysis.estimated_hours_min, analysis.estimated_hours_max)}
          </span>
          {analysis.required_skills.slice(0, 4).map((skill) => (
            <Chip
              key={skill}
              tone={
                matched_skills.some((m) => m.skill === skill) ? "accent" : "neutral"
              }
            >
              {skill}
            </Chip>
          ))}
        </div>
      ) : null}

      <ul className="mt-4 space-y-1 text-[13px] leading-relaxed text-muted">
        {reasoning.slice(0, 3).map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>

      {skill_gaps.length ? (
        <p className="mt-3 text-[13px] text-muted">
          <span className="text-warn">Gap</span>{" "}
          {skill_gaps
            .slice(0, 2)
            .map((g) => `${g.skill} (~${Math.round(g.learning_hours)}h)`)
            .join(", ")}
        </p>
      ) : null}

      <div className="mt-5 flex items-center justify-between gap-4 border-t border-line pt-4">
        <RepositoryHealth health={issue.repository.health} compact />
        <div className="flex shrink-0 gap-2">
          <Button href={`/issues/${issue.id}`} variant="ghost">
            Understand issue
          </Button>
          <Button href={`/workspace/${issue.id}`}>
            Start contribution
            <ArrowRight size={14} weight="bold" />
          </Button>
        </div>
      </div>
    </article>
  );
}
