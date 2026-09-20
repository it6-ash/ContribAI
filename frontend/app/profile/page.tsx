"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowClockwise } from "@phosphor-icons/react/dist/ssr";
import { api, ApiError } from "@/lib/api";
import { Nav } from "@/components/Nav";
import { SkillGraph } from "@/components/SkillGraph";
import {
  Button,
  ErrorState,
  SectionTitle,
  Skeleton,
} from "@/components/primitives";
import type { Profile, Taxonomy } from "@/lib/types";

const EXPERIENCE_LABEL: Record<string, string> = {
  never_contributed: "Never contributed",
  developer: "Built projects",
  some_oss: "Some contributions",
  experienced: "Experienced contributor",
};

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [p, t] = await Promise.all([api.profile(), api.taxonomy()]);
      setProfile(p);
      setTaxonomy(t);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/onboarding");
        return;
      }
      setError(err instanceof ApiError ? err.message : "Could not load your profile.");
    }
  }, [router]);

  useEffect(() => {
    load();
  }, [load]);

  async function save(payload: { mode?: string; experience_level?: string }) {
    setSaving(true);
    try {
      setProfile(await api.updateProfile(payload));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  async function reanalyze() {
    setAnalyzing(true);
    setError(null);
    try {
      setProfile(await api.analyzeProfile());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not re-analyse.");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-[1100px] flex-1 px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Your skill graph</h1>
            <p className="mt-2 max-w-[62ch] text-[14px] leading-relaxed text-muted">
              Built from GitHub evidence: repository languages, dependency manifests,
              commit recency and merged pull requests. Expand a skill to see what
              produced it.
            </p>
          </div>
          {profile && !profile.user.is_demo ? (
            <Button variant="ghost" onClick={reanalyze} disabled={analyzing}>
              <ArrowClockwise size={14} className={analyzing ? "animate-spin" : ""} />
              {analyzing ? "Reading GitHub" : "Re-analyse GitHub"}
            </Button>
          ) : null}
        </div>

        {error ? (
          <div className="mt-8">
            <ErrorState message={error} retry={load} />
          </div>
        ) : null}

        {profile?.user.is_demo ? (
          <p className="mt-6 rounded-[10px] border border-line bg-surface p-4 text-[13.5px] leading-relaxed text-muted">
            This is a demo profile with a fixed skill graph, so recommendations are
            reproducible. Sign in with GitHub to build one from a real account.
          </p>
        ) : null}

        <section className="mt-10">
          <SectionTitle>Preferences</SectionTitle>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <label
                htmlFor="mode"
                className="mb-2 block text-[13px] font-medium"
              >
                What you are looking for
              </label>
              <select
                id="mode"
                value={profile?.user.mode ?? ""}
                disabled={!profile || saving}
                onChange={(e) => save({ mode: e.target.value })}
                className="w-full rounded-[10px] border border-line bg-surface px-3 py-2 text-[14px] text-foreground disabled:opacity-50"
              >
                {Object.entries(taxonomy?.modes ?? {}).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-[12.5px] leading-relaxed text-muted">
                Changing this re-ranks your dashboard immediately.
              </p>
            </div>

            <div>
              <label
                htmlFor="experience"
                className="mb-2 block text-[13px] font-medium"
              >
                Experience level
              </label>
              <select
                id="experience"
                value={profile?.user.experience_level ?? ""}
                disabled={!profile || saving}
                onChange={(e) => save({ experience_level: e.target.value })}
                className="w-full rounded-[10px] border border-line bg-surface px-3 py-2 text-[14px] text-foreground disabled:opacity-50"
              >
                {(taxonomy?.experience_levels ?? []).map((value) => (
                  <option key={value} value={value}>
                    {EXPERIENCE_LABEL[value] ?? value}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-[12.5px] leading-relaxed text-muted">
                Sets the difficulty band we aim at, and the effort ceiling per issue.
              </p>
            </div>
          </div>
        </section>

        <section className="mt-12">
          <SectionTitle
            right={
              profile ? (
                <span className="font-mono text-[12px] text-muted">
                  {profile.skills.length} skills
                </span>
              ) : null
            }
          >
            Skills
          </SectionTitle>
          {profile ? (
            <SkillGraph skillsByCategory={profile.skills_by_category} />
          ) : (
            <Skeleton className="h-72 w-full" />
          )}
        </section>

        {taxonomy ? (
          <section className="mt-14 border-t border-line pt-10">
            <SectionTitle>How the fit score is weighted</SectionTitle>
            <div className="grid gap-x-10 gap-y-1.5 sm:grid-cols-2">
              {Object.entries(taxonomy.weights).map(([key, weight]) => (
                <div
                  key={key}
                  className="flex items-center justify-between border-b border-line py-1.5"
                >
                  <span className="text-[13px] text-muted">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono text-[12px]">
                    {Math.round(weight * 100)}%
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-4 max-w-[68ch] text-[12.5px] leading-relaxed text-muted">
              These weights are an internal heuristic, not a validated model. They are
              shown because a ranking you cannot inspect is a ranking you cannot trust.
            </p>
          </section>
        ) : null}
      </main>
    </>
  );
}
