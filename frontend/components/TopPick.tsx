"use client";

import Link from "next/link";
import { ArrowRight, ArrowSquareOut, Clock, GitBranch } from "@phosphor-icons/react/dist/ssr";
import { hoursLabel } from "@/lib/api";
import type { Recommendation } from "@/lib/types";
import { Chip, DifficultyBadge } from "./primitives";

/** The answer, stated once, in full.
 *
 *  The dashboard used to open with a funnel chart and a scoring grid, which are
 *  both commentary on how the ranking works rather than what to do about it.
 *  This is the thing the reader came for: one issue, its whole title, why it
 *  was chosen, and what it would cost them.
 */
export function TopPick({ rec }: { rec: Recommendation }) {
  const { issue } = rec;
  const a = issue.analysis;
  const coreGaps = rec.skill_gaps.filter((g) => g.severity === "core");
  const ready = Math.round((rec.readiness.overall ?? 0) * 100);

  return (
    <article className="panel relative overflow-hidden p-6 lg:p-8">
      {/* The one accent wash on the page, so this block reads as the answer
          and every card below it reads as an alternative. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(38rem 18rem at 0% 0%, rgba(91,156,255,0.10), transparent 70%)",
        }}
      />

      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="rounded-full bg-accent px-2.5 py-1 font-mono text-[10.5px] font-medium uppercase tracking-[0.12em] text-[#06070a]">
          Start here
        </span>
        <span className="inline-flex items-center gap-1.5 font-mono text-[12.5px] text-muted">
          <GitBranch size={13} />
          {issue.repository.full_name}
          <span className="text-muted/60">#{issue.number}</span>
        </span>
        {issue.is_demo ? (
          <span className="font-mono text-[11px] text-warn">sample issue</span>
        ) : null}
      </div>

      {/* Full title. Truncating this made the list unreadable: you could not
          tell what any of the issues actually were. */}
      <h2 className="mt-4 max-w-[26ch] text-[26px] font-semibold leading-[1.15] tracking-tight lg:text-[32px]">
        <Link href={`/issues/${issue.id}`} className="hover:text-accent">
          {issue.title}
        </Link>
      </h2>

      {a ? (
        <p className="mt-4 max-w-[68ch] text-[15px] leading-relaxed text-muted">
          {a.summary}
        </p>
      ) : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <div>
          <h3 className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
            Why you
          </h3>
          <ul className="mt-3 space-y-1.5 text-[14px] leading-relaxed">
            {rec.reasoning.slice(0, 4).map((line) => (
              <li key={line} className="text-muted">
                {line}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
            What it costs you
          </h3>
          <dl className="mt-3 space-y-2 text-[14px]">
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted">Effort</dt>
              <dd className="inline-flex items-center gap-1.5 font-mono text-[13px]">
                <Clock size={13} className="text-muted" />
                {a ? hoursLabel(a.estimated_hours_min, a.estimated_hours_max) : "unknown"}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted">Level</dt>
              <dd>{a ? <DifficultyBadge level={a.difficulty} /> : "—"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-muted">You are ready</dt>
              <dd className="font-mono text-[13px] tnum">{ready}%</dd>
            </div>
            <div className="flex items-start justify-between gap-3">
              <dt className="shrink-0 text-muted">To learn first</dt>
              <dd className="text-right font-mono text-[12.5px]">
                {coreGaps.length ? (
                  <span className="text-warn">
                    {coreGaps.map((g) => g.skill).join(", ")}
                  </span>
                ) : (
                  <span className="text-ok">nothing blocking</span>
                )}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {a?.required_skills.length ? (
        <div className="mt-6 flex flex-wrap gap-1.5">
          {a.required_skills.slice(0, 7).map((s) => (
            <Chip
              key={s}
              tone={rec.matched_skills.some((m) => m.skill === s) ? "accent" : "neutral"}
            >
              {s}
            </Chip>
          ))}
        </div>
      ) : null}

      <div className="mt-7 flex flex-wrap items-center gap-3 border-t border-line pt-6">
        <Link
          href={`/workspace/${issue.id}`}
          className="group inline-flex items-center gap-2 rounded-[10px] bg-accent px-5 py-2.5 text-[14px] font-medium text-[#06070a]"
        >
          Start contributing
          <ArrowRight size={14} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
        </Link>
        <Link
          href={`/issues/${issue.id}`}
          className="inline-flex items-center rounded-[10px] border border-line px-5 py-2.5 text-[14px] font-medium transition-colors hover:border-muted/50"
        >
          Understand it first
        </Link>
        {!issue.is_demo ? (
          <a
            href={issue.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-[13px] text-muted hover:text-foreground"
          >
            Open on GitHub
            <ArrowSquareOut size={12} />
          </a>
        ) : null}
      </div>
    </article>
  );
}
