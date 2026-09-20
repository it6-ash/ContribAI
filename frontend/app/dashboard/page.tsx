"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowClockwise, CaretDown } from "@phosphor-icons/react/dist/ssr";
import { api, ApiError } from "@/lib/api";
import { Nav } from "@/components/Nav";
import { IssueCard } from "@/components/IssueCard";
import { MatchHeatmap } from "@/components/MatchHeatmap";
import { TopPick } from "@/components/TopPick";
import { FilterFunnel } from "@/components/viz";
import {
  applyFilters,
  DashboardControls,
  EMPTY_FILTERS,
  type Filters,
} from "@/components/DashboardControls";
import {
  Button,
  EmptyState,
  ErrorState,
  SectionTitle,
  Skeleton,
} from "@/components/primitives";
import type { Profile, RecommendationsResponse } from "@/lib/types";

const BUCKET_ORDER = ["best_fit", "skill_stretch", "gentle_start", "worth_a_look"];
const BUCKET_TITLE: Record<string, string> = {
  best_fit: "Best fit",
  skill_stretch: "Skill stretch",
  gentle_start: "Gentle start",
  worth_a_look: "Worth a look",
};

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  // Analytics are commentary on the ranking, not the answer. Closed by default.
  const [showWorkings, setShowWorkings] = useState(false);

  const load = useCallback(
    async (refresh = false) => {
      setError(null);
      if (refresh) setRefreshing(true);
      try {
        const [p, recs] = await Promise.all([
          api.profile(),
          api.recommendations(12, refresh),
        ]);
        setProfile(p);
        setData(recs);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.push("/onboarding");
          return;
        }
        setError(err instanceof ApiError ? err.message : "Could not load your dashboard.");
      } finally {
        setRefreshing(false);
      }
    },
    [router],
  );

  useEffect(() => {
    load();
  }, [load]);

  const all = data?.recommendations ?? [];
  const visible = applyFilters(all, filters);
  // Buckets are the editorial shelves; once the reader starts filtering or
  // re-sorting they are steering themselves, so get out of the way and show
  // one ranked list instead.
  const steering =
    filters.sort !== "fit" ||
    filters.difficulty.size > 0 ||
    filters.repos.size > 0 ||
    filters.tags.size > 0 ||
    filters.tiers.size > 0 ||
    filters.hideGaps;
  // The hero already shows visible[0]; listing it again reads as a duplicate.
  const rest = steering ? visible : visible.slice(1);
  const grouped = BUCKET_ORDER.map((bucket) => ({
    bucket,
    items: rest.filter((r) => r.bucket === bucket),
  })).filter((g) => g.items.length);

  const stats = data?.stats;
  const topSkills = (profile?.skills ?? []).slice(0, 6);

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {profile ? `Welcome back, ${profile.user.username}` : "Your contributions"}
            </h1>
            {stats ? (
              <p className="mt-2 max-w-[54ch] text-[14.5px] leading-relaxed text-muted">
                {stats.strong_matches
                  ? `${stats.strong_matches} of the ${stats.analyzed} open issues we checked are a strong fit for what you already know.`
                  : `We checked ${stats.analyzed} open issues. None is a strong fit yet, so these are the closest.`}
              </p>
            ) : (
              <Skeleton className="mt-3 h-4 w-72" />
            )}
          </div>

          <div className="flex items-center gap-2">
            {profile && !profile.user.is_demo ? (
              <Button variant="ghost" onClick={() => load(true)} disabled={refreshing}>
                <ArrowClockwise
                  size={14}
                  className={refreshing ? "animate-spin" : ""}
                />
                {refreshing ? "Searching GitHub" : "Refresh from GitHub"}
              </Button>
            ) : null}
            <Button variant="ghost" href="/profile">
              Edit profile
            </Button>
          </div>
        </div>

        {topSkills.length ? (
          <div className="mt-6 flex flex-wrap items-center gap-2">
            <span className="mr-1 text-[12.5px] text-muted">
              Matching against your strongest skills:
            </span>
            {topSkills.map((s) => (
              <span
                key={s.name}
                className="rounded border border-line px-2 py-1 font-mono text-[11.5px] text-muted"
                title={s.evidence.join(" · ")}
              >
                {s.name}
                <span className="ml-1 text-muted/60">
                  {Math.round(s.confidence * 100)}% confidence
                </span>
              </span>
            ))}
            <Link
              href="/profile"
              className="text-[12.5px] text-accent underline underline-offset-4"
            >
              full skill graph
            </Link>
          </div>
        ) : null}

        {error ? (
          <div className="mt-10">
            <ErrorState message={error} retry={() => load()} />
          </div>
        ) : null}

        {/* The answer, before any commentary about how it was reached. */}
        {!steering && visible.length ? (
          <div className="mt-8">
            <TopPick rec={visible[0]} />
          </div>
        ) : null}

        {all.length > 1 ? (
          <div className="mt-10">
            <button
              onClick={() => setShowWorkings((v) => !v)}
              aria-expanded={showWorkings}
              className="flex items-center gap-2 text-[13.5px] text-muted transition-colors hover:text-foreground"
            >
              <CaretDown
                size={13}
                className={`transition-transform ${showWorkings ? "rotate-180" : ""}`}
              />
              {showWorkings ? "Hide" : "Show"} how these were ranked
            </button>

            {showWorkings ? (
              <div className="mt-4 space-y-4">
                {stats?.analyzed ? (
                  <div className="panel p-5">
                    <FilterFunnel
                      analyzed={stats.analyzed}
                      passed={stats.passed_filters ?? 0}
                      strong={stats.strong_matches ?? 0}
                      dropped={stats.dropped ?? {}}
                    />
                  </div>
                ) : null}
                <MatchHeatmap recs={visible.slice(0, 10)} />
              </div>
            ) : null}
          </div>
        ) : null}

        {all.length > 1 ? (
          <div className="mt-8">
            <DashboardControls
              recs={all}
              filters={filters}
              onChange={setFilters}
              shown={visible.length}
            />
          </div>
        ) : null}

        {!data && !error ? (
          <div className="mt-10 space-y-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-56 w-full" />
            ))}
          </div>
        ) : null}

        {data && grouped.length === 0 && !error ? (
          <div className="mt-10">
            <EmptyState
              title="Nothing cleared the filters"
              body="Every candidate issue was assigned, already had a pull request open, or sat outside your selected technologies. Widen the search by switching to skill-stretch mode, which allows issues needing one or two technologies you do not know yet."
              action={
                <Button href="/profile">Change mode</Button>
              }
            />
          </div>
        ) : null}

        {steering ? (
          <div className="mt-10 space-y-4">
            {rest.map((rec, i) => (
              <IssueCard key={rec.issue.id} rec={rec} index={i} />
            ))}
            {visible.length === 0 ? (
              <EmptyState
                title="Nothing matches those filters"
                body="Every recommendation was excluded by the level, repository or readiness filters above."
                action={
                  <Button
                    variant="ghost"
                    onClick={() => setFilters({ ...EMPTY_FILTERS, sort: filters.sort })}
                  >
                    Clear filters
                  </Button>
                }
              />
            ) : null}
          </div>
        ) : (
        <div className="mt-10 space-y-12">
          {grouped.map(({ bucket, items }) => (
            <section key={bucket}>
              <SectionTitle
                right={
                  <span className="font-mono text-[12px] text-muted">
                    {items.length}
                  </span>
                }
              >
                {BUCKET_TITLE[bucket] ?? bucket}
              </SectionTitle>
              <div className="space-y-4">
                {items.map((rec, i) => (
                  <IssueCard key={rec.issue.id} rec={rec} index={i} />
                ))}
              </div>
            </section>
          ))}
        </div>
        )}
      </main>
    </>
  );
}
