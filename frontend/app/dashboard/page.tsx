"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowClockwise } from "@phosphor-icons/react/dist/ssr";
import { api, ApiError } from "@/lib/api";
import { Nav } from "@/components/Nav";
import { IssueCard } from "@/components/IssueCard";
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

  const load = useCallback(
    async (refresh = false) => {
      setError(null);
      if (refresh) setRefreshing(true);
      try {
        const [p, recs] = await Promise.all([
          api.profile(),
          api.recommendations(6, refresh),
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

  const grouped = BUCKET_ORDER.map((bucket) => ({
    bucket,
    items: (data?.recommendations ?? []).filter((r) => r.bucket === bucket),
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
              <p className="mt-2 font-mono text-[13px] text-muted">
                {stats.analyzed} issues analysed · {stats.passed_filters} passed filters ·{" "}
                {stats.strong_matches} strong matches
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
            {topSkills.map((s) => (
              <span
                key={s.name}
                className="rounded border border-line px-2 py-1 font-mono text-[11.5px] text-muted"
                title={s.evidence.join(" · ")}
              >
                {s.name}{" "}
                <span className="text-muted/60">{Math.round(s.confidence * 100)}</span>
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

        {stats?.dropped && Object.keys(stats.dropped).length ? (
          <p className="mt-8 border-t border-line pt-5 font-mono text-[12px] leading-relaxed text-muted">
            filtered out:{" "}
            {Object.entries(stats.dropped)
              .map(([reason, count]) => `${count} ${reason}`)
              .join(" · ")}
          </p>
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
      </main>
    </>
  );
}
