"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowSquareOut, Sparkle } from "@phosphor-icons/react/dist/ssr";
import { api, ApiError } from "@/lib/api";
import { Nav } from "@/components/Nav";
import { IssueExplanation } from "@/components/IssueExplanation";
import { MatchScore, ReadinessPanel } from "@/components/MatchScore";
import { RepositoryHealth } from "@/components/RepositoryHealth";
import { SkillGapPanel } from "@/components/SkillGap";
import {
  Button,
  Chip,
  ErrorState,
  SectionTitle,
  Skeleton,
} from "@/components/primitives";
import type { Issue, Recommendation } from "@/lib/types";

export default function IssuePage({ params }: PageProps<"/issues/[id]">) {
  const { id } = use(params);
  const issueId = Number(id);

  const [issue, setIssue] = useState<Issue | null>(null);
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api.issue(issueId);
      setIssue(data);
      // The matching detail comes from the user's recommendation set, so the page
      // shows the same numbers the dashboard ranked on.
      const recs = await api.recommendations(20).catch(() => null);
      setRec(recs?.recommendations.find((r) => r.issue.id === issueId) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load this issue.");
    }
  }, [issueId]);

  useEffect(() => {
    load();
  }, [load]);

  async function explain() {
    setExplaining(true);
    try {
      setIssue(await api.explainIssue(issueId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not analyse this issue.");
    } finally {
      setExplaining(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-6 py-10">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-[13px] text-muted hover:text-foreground"
        >
          <ArrowLeft size={13} />
          Back to recommendations
        </Link>

        {error ? (
          <div className="mt-8">
            <ErrorState message={error} retry={load} />
          </div>
        ) : null}

        {!issue && !error ? (
          <div className="mt-8 space-y-4">
            <Skeleton className="h-10 w-2/3" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : null}

        {issue ? (
          <>
            <header className="mt-6 flex flex-wrap items-start justify-between gap-6">
              <div className="min-w-0">
                <p className="font-mono text-[13px] text-muted">
                  {issue.repository.full_name}{" "}
                  <span className="text-muted/60">#{issue.number}</span>
                </p>
                <h1 className="mt-2 max-w-[26ch] text-2xl font-semibold leading-tight tracking-tight md:text-3xl">
                  {issue.title}
                </h1>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {issue.labels.map((label) => (
                    <Chip key={label}>{label}</Chip>
                  ))}
                </div>
              </div>

              <div className="flex shrink-0 gap-2">
                <Button variant="ghost" href={issue.url}>
                  View on GitHub
                  <ArrowSquareOut size={13} />
                </Button>
                <Button href={`/workspace/${issue.id}`}>Start contribution</Button>
              </div>
            </header>

            <div className="mt-10 grid gap-10 lg:grid-cols-[1.35fr_0.65fr]">
              <div className="space-y-12">
                <section>
                  <SectionTitle
                    right={
                      issue.analysis?.source !== "llm" ? (
                        <button
                          onClick={explain}
                          disabled={explaining}
                          className="inline-flex items-center gap-1.5 text-[13px] text-accent disabled:opacity-50"
                        >
                          <Sparkle size={13} weight="fill" />
                          {explaining ? "Analysing..." : "Explain in depth"}
                        </button>
                      ) : null
                    }
                  >
                    Understanding this issue
                  </SectionTitle>
                  {issue.analysis ? (
                    <IssueExplanation analysis={issue.analysis} />
                  ) : (
                    <Skeleton className="h-48 w-full" />
                  )}
                </section>

                {rec ? (
                  <section>
                    <SectionTitle>Why this issue, for you</SectionTitle>
                    <ul className="mb-6 space-y-1.5 text-[14px] leading-relaxed text-muted">
                      {rec.reasoning.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                    <MatchScore rec={rec} />
                  </section>
                ) : null}

                {rec ? (
                  <section>
                    <SectionTitle>Skill gap</SectionTitle>
                    <SkillGapPanel
                      matched={rec.matched_skills}
                      gaps={rec.skill_gaps}
                      narrative={rec.skill_gap_narrative}
                    />
                  </section>
                ) : null}

                <section>
                  <SectionTitle>Original issue text</SectionTitle>
                  <pre className="scroll-thin panel max-h-[420px] overflow-auto p-5 font-mono text-[12.5px] leading-relaxed whitespace-pre-wrap text-muted">
                    {issue.body || "(empty)"}
                  </pre>
                </section>
              </div>

              <aside className="space-y-10">
                {rec ? (
                  <section className="panel p-5">
                    <h2 className="mb-4 text-[15px] font-semibold tracking-tight">
                      Readiness
                    </h2>
                    <ReadinessPanel rec={rec} />
                  </section>
                ) : null}

                <section className="panel p-5">
                  <h2 className="mb-1 text-[15px] font-semibold tracking-tight">
                    {issue.repository.full_name}
                  </h2>
                  <p className="mb-4 text-[13px] leading-relaxed text-muted">
                    {issue.repository.description}
                  </p>
                  <RepositoryHealth health={issue.repository.health} />
                </section>
              </aside>
            </div>
          </>
        ) : null}
      </main>
    </>
  );
}
