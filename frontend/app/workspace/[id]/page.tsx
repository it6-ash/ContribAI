"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowSquareOut } from "@phosphor-icons/react/dist/ssr";
import { api, ApiError, hoursLabel } from "@/lib/api";
import { Nav } from "@/components/Nav";
import { AskAI } from "@/components/AskAI";
import { ContributionRoadmap } from "@/components/ContributionRoadmap";
import { IssueExplanation } from "@/components/IssueExplanation";
import { RepositoryHealth } from "@/components/RepositoryHealth";
import { SkillGapPanel } from "@/components/SkillGap";
import {
  Button,
  Chip,
  DifficultyBadge,
  ErrorState,
  Skeleton,
} from "@/components/primitives";
import type { Issue, Plan, Recommendation, Repository } from "@/lib/types";

const TABS = ["Overview", "Issue", "Repository", "Skill gap", "Plan"] as const;
type Tab = (typeof TABS)[number];

export default function WorkspacePage({ params }: PageProps<"/workspace/[id]">) {
  const { id } = use(params);
  const issueId = Number(id);

  const [tab, setTab] = useState<Tab>("Overview");
  const [issue, setIssue] = useState<Issue | null>(null);
  const [repo, setRepo] = useState<Repository | null>(null);
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api.issue(issueId);
      setIssue(data);
      const [full, recs, planned] = await Promise.all([
        api.repository(data.repository.id).catch(() => null),
        api.recommendations(20).catch(() => null),
        api.plan(issueId).catch(() => null),
      ]);
      setRepo(full);
      setRec(recs?.recommendations.find((r) => r.issue.id === issueId) ?? null);
      setPlan(planned);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not open this workspace.");
    }
  }, [issueId]);

  useEffect(() => {
    load();
  }, [load]);

  const analysis = issue?.analysis;

  return (
    <>
      <Nav />
      <main className="mx-auto flex w-full max-w-[1400px] flex-1 flex-col px-6 py-8">
        <Link
          href={`/issues/${issueId}`}
          className="inline-flex items-center gap-1.5 text-[13px] text-muted hover:text-foreground"
        >
          <ArrowLeft size={13} />
          Back to issue
        </Link>

        {error ? (
          <div className="mt-8">
            <ErrorState message={error} retry={load} />
          </div>
        ) : null}

        {!issue && !error ? (
          <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_360px]">
            <Skeleton className="h-[520px] w-full" />
            <Skeleton className="h-[520px] w-full" />
          </div>
        ) : null}

        {issue ? (
          <div className="mt-6 grid flex-1 gap-6 lg:grid-cols-[1fr_360px]">
            <div className="min-w-0">
              <header className="panel p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-mono text-[12.5px] text-muted">
                      {issue.repository.full_name}{" "}
                      <span className="text-muted/60">#{issue.number}</span>
                    </p>
                    <h1 className="mt-1.5 text-[18px] font-semibold leading-snug tracking-tight">
                      {issue.title}
                    </h1>
                  </div>
                  {issue.is_demo ? (
                    <span className="shrink-0 font-mono text-[11.5px] text-warn">
                      sample issue
                    </span>
                  ) : (
                    <a
                      href={issue.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex shrink-0 items-center gap-1.5 text-[13px] text-muted hover:text-foreground"
                    >
                      GitHub
                      <ArrowSquareOut size={12} />
                    </a>
                  )}
                </div>
                {analysis ? (
                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    <DifficultyBadge level={analysis.difficulty} />
                    <span className="font-mono text-[11.5px] text-muted">
                      {hoursLabel(
                        analysis.estimated_hours_min,
                        analysis.estimated_hours_max,
                      )}
                    </span>
                    {rec ? (
                      <span className="font-mono text-[11.5px] text-accent">
                        {Math.round(rec.fit_score * 100)}% fit ·{" "}
                        {Math.round((rec.readiness.overall ?? 0) * 100)}% ready
                      </span>
                    ) : null}
                  </div>
                ) : null}
              </header>

              <nav className="mt-5 flex gap-1 border-b border-line" role="tablist">
                {TABS.map((name) => (
                  <button
                    key={name}
                    role="tab"
                    aria-selected={tab === name}
                    onClick={() => setTab(name)}
                    className={`-mb-px border-b-2 px-3 py-2 text-[13.5px] transition-colors ${
                      tab === name
                        ? "border-accent text-foreground"
                        : "border-transparent text-muted hover:text-foreground"
                    }`}
                  >
                    {name}
                  </button>
                ))}
              </nav>

              <div className="py-6">
                {tab === "Overview" ? (
                  <div className="space-y-8">
                    {analysis ? (
                      <p className="max-w-[70ch] text-[15px] leading-relaxed">
                        {analysis.summary}
                      </p>
                    ) : null}
                    {rec ? (
                      <ul className="space-y-1.5 text-[14px] leading-relaxed text-muted">
                        {rec.reasoning.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    ) : null}
                    {analysis?.affected_files.length ? (
                      <section>
                        <h2 className="mb-3 text-[14px] font-semibold">
                          Where to start reading
                        </h2>
                        <ol className="space-y-1.5">
                          {analysis.affected_files.map((f, i) => (
                            <li
                              key={f}
                              className="flex items-baseline gap-3 font-mono text-[12.5px]"
                            >
                              <span className="text-muted">
                                {String(i + 1).padStart(2, "0")}
                              </span>
                              <span className={i === 0 ? "text-accent" : ""}>{f}</span>
                            </li>
                          ))}
                        </ol>
                      </section>
                    ) : null}
                    {repo?.setup_commands?.length ? (
                      <section>
                        <h2 className="mb-3 text-[14px] font-semibold">Setup</h2>
                        <div className="panel-2 divide-y divide-line">
                          {repo.setup_commands.map((cmd) => (
                            <p
                              key={cmd}
                              className="px-4 py-2 font-mono text-[12.5px] text-muted"
                            >
                              <span className="select-none text-muted/60">$ </span>
                              {cmd}
                            </p>
                          ))}
                        </div>
                      </section>
                    ) : null}
                  </div>
                ) : null}

                {tab === "Issue" ? (
                  analysis ? (
                    <IssueExplanation analysis={analysis} />
                  ) : (
                    <Skeleton className="h-64 w-full" />
                  )
                ) : null}

                {tab === "Repository" ? (
                  <div className="space-y-8">
                    <div>
                      <h2 className="text-[15px] font-semibold">
                        {issue.repository.full_name}
                      </h2>
                      <p className="mt-1.5 max-w-[68ch] text-[14px] leading-relaxed text-muted">
                        {issue.repository.description}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {issue.repository.topics.map((t) => (
                          <Chip key={t}>{t}</Chip>
                        ))}
                      </div>
                    </div>
                    <RepositoryHealth health={issue.repository.health} />
                    {repo?.tree?.length ? (
                      <section>
                        <h3 className="mb-3 text-[14px] font-semibold">
                          Repository tree
                        </h3>
                        <pre className="scroll-thin panel max-h-[380px] overflow-auto p-4 font-mono text-[12px] leading-relaxed text-muted">
                          {repo.tree.join("\n")}
                        </pre>
                      </section>
                    ) : null}
                  </div>
                ) : null}

                {tab === "Skill gap" ? (
                  rec ? (
                    <SkillGapPanel
                      matched={rec.matched_skills}
                      gaps={rec.skill_gaps}
                      narrative={rec.skill_gap_narrative}
                    />
                  ) : (
                    <p className="text-[14px] text-muted">
                      No match record for this issue yet. Open it from your dashboard
                      recommendations to see the gap analysis.
                    </p>
                  )
                ) : null}

                {tab === "Plan" ? (
                  plan ? (
                    <>
                      <div className="mb-5 flex justify-end">
                        <Button
                          variant="ghost"
                          onClick={async () => {
                            setPlan(null);
                            setPlan(await api.plan(issueId, true));
                          }}
                        >
                          Regenerate plan
                        </Button>
                      </div>
                      <ContributionRoadmap plan={plan} />
                    </>
                  ) : (
                    <div className="space-y-3">
                      {[0, 1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-16 w-full" />
                      ))}
                    </div>
                  )
                ) : null}
              </div>
            </div>

            <aside className="panel flex h-[calc(100dvh-180px)] flex-col p-5 lg:sticky lg:top-24">
              <h2 className="mb-1 text-[15px] font-semibold tracking-tight">
                Contribution assistant
              </h2>
              <p className="mb-4 font-mono text-[11px] text-muted">
                scoped to this issue and repository
              </p>
              <div className="min-h-0 flex-1">
                <AskAI issueId={issueId} />
              </div>
            </aside>
          </div>
        ) : null}
      </main>
    </>
  );
}
