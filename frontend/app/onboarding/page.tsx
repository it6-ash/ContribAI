"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, GithubLogo } from "@phosphor-icons/react/dist/ssr";
import { api, ApiError } from "@/lib/api";
import { Nav } from "@/components/Nav";
import { Button, ErrorState, Skeleton } from "@/components/primitives";
import { SkillPicker, type PickedSkill } from "@/components/SkillPicker";
import type { Health, Taxonomy, User } from "@/lib/types";

const EXPERIENCE: Array<[string, string, string]> = [
  ["never_contributed", "Never contributed", "I can code, but I have never opened a PR on someone else's project."],
  ["developer", "Built projects", "I ship my own work but have not contributed to open source."],
  ["some_oss", "Some contributions", "A handful of merged PRs on other people's repositories."],
  ["experienced", "Experienced contributor", "I contribute regularly and want work worth my time."],
];

const MODE_HELP: Record<string, string> = {
  first_contribution: "Lower complexity, clear issues, active maintainers.",
  developer_match: "Realistic difficulty for your current stack.",
  skill_stretch: "Allows one or two technologies you do not know yet, shown explicitly.",
  high_impact: "Harder work in bigger codebases.",
};

const DEMO_BLURB: Record<string, string> = {
  alex: "Python, FastAPI, Docker. Ships side projects, never contributed.",
  priya: "TypeScript, React, accessibility. A few merged PRs.",
  rahul: "Go, Kubernetes, distributed systems. Maintains two tools.",
};

function OnboardingInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [health, setHealth] = useState<Health | null>(null);
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [experience, setExperience] = useState("developer");
  const [mode, setMode] = useState("developer_match");
  const [skills, setSkills] = useState<PickedSkill[]>([]);
  // Set once the GitHub OAuth callback has redirected back here signed in.
  const [githubUser, setGithubUser] = useState<User | null>(null);

  useEffect(() => {
    Promise.all([api.health(), api.taxonomy()])
      .then(([h, t]) => {
        setHealth(h);
        setTaxonomy(t);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Could not load setup data."),
      );
    // A real account arriving from the OAuth callback has no skill graph yet.
    api
      .me()
      .then((u) => !u.is_demo && setGithubUser(u))
      .catch(() => setGithubUser(null));
  }, []);

  async function finishGithub() {
    setBusy("github");
    setError(null);
    try {
      await api.updateProfile({
        experience_level: experience,
        mode,
        skills,
      });
      // Reads repositories, manifests and merged PRs. Slow, so it gets its own
      // step with visible progress rather than happening behind a spinner.
      await api.analyzeProfile();
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not analyse your GitHub profile.",
      );
      setBusy(null);
    }
  }

  async function startDemo(username: string) {
    setBusy(username);
    setError(null);
    try {
      await api.loginDemo(username);
      await api.updateProfile({
        experience_level: experience,
        mode,
        skills,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the demo.");
      setBusy(null);
    }
  }

  const wantsDemo = params.get("demo") === "1";

  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-[880px] flex-1 px-6 py-16">
        <h1 className="text-3xl font-semibold tracking-tight">
          Tell us where you are
        </h1>
        <p className="mt-3 max-w-[58ch] text-[15px] leading-relaxed text-muted">
          This shapes which issues you see. You can change it later without losing
          anything.
        </p>

        {error ? (
          <div className="mt-8">
            <ErrorState message={error} retry={() => location.reload()} />
          </div>
        ) : null}

        <section className="mt-12">
          <h2 className="mb-4 text-[15px] font-semibold">Experience</h2>
          <div className="grid gap-px overflow-hidden rounded-[10px] border border-line bg-line sm:grid-cols-2">
            {EXPERIENCE.map(([value, label, help]) => (
              <button
                key={value}
                onClick={() => setExperience(value)}
                aria-pressed={experience === value}
                className={`bg-surface p-4 text-left transition-colors ${
                  experience === value ? "bg-surface-2" : "hover:bg-surface-2/60"
                }`}
              >
                <span className="flex items-center gap-2 text-[14px] font-medium">
                  <span
                    className={`size-2 rounded-full ${
                      experience === value ? "bg-accent" : "bg-line"
                    }`}
                  />
                  {label}
                </span>
                <span className="mt-1.5 block text-[13px] leading-relaxed text-muted">
                  {help}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="mb-4 text-[15px] font-semibold">What are you looking for</h2>
          {taxonomy ? (
            <div className="grid gap-px overflow-hidden rounded-[10px] border border-line bg-line sm:grid-cols-2">
              {Object.entries(taxonomy.modes).map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => setMode(value)}
                  aria-pressed={mode === value}
                  className={`bg-surface p-4 text-left transition-colors ${
                    mode === value ? "bg-surface-2" : "hover:bg-surface-2/60"
                  }`}
                >
                  <span className="flex items-center gap-2 text-[14px] font-medium">
                    <span
                      className={`size-2 rounded-full ${
                        mode === value ? "bg-accent" : "bg-line"
                      }`}
                    />
                    {label}
                  </span>
                  <span className="mt-1.5 block text-[13px] leading-relaxed text-muted">
                    {MODE_HELP[value]}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </section>

        <section className="mt-10">
          <h2 className="text-[15px] font-semibold">Anything we would miss</h2>
          <p className="mb-4 mt-1.5 max-w-[58ch] text-[13.5px] leading-relaxed text-muted">
            Optional. Skills you know that your public repositories do not show. These
            are marked self-reported and weighted below GitHub evidence.
          </p>
          {taxonomy ? (
            <SkillPicker taxonomy={taxonomy} picked={skills} onChange={setSkills} />
          ) : (
            <Skeleton className="h-40 w-full" />
          )}
        </section>

        <section className="mt-14 border-t border-line pt-10">
          <h2 className="text-[15px] font-semibold">
            {githubUser ? `Signed in as @${githubUser.username}` : "Connect your GitHub"}
          </h2>
          <p className="mb-5 mt-1.5 max-w-[58ch] text-[13.5px] leading-relaxed text-muted">
            {githubUser
              ? "Next we read your public repositories, dependency manifests and merged pull requests to build your skill graph. This takes a few seconds and only happens when you ask for it."
              : "Read-only access to your public profile. We never request repository write scope, and the access token stays encrypted on the server."}
          </p>

          {githubUser ? (
            <Button onClick={finishGithub} disabled={busy !== null}>
              {busy === "github"
                ? "Reading your GitHub..."
                : "Build my skill graph"}
            </Button>
          ) : health?.github_oauth_configured ? (
            <Button href={api.githubLoginUrl()}>
              <GithubLogo size={16} weight="fill" />
              Continue with GitHub
            </Button>
          ) : (
            <p className="rounded-[10px] border border-line bg-surface p-4 text-[13.5px] leading-relaxed text-muted">
              GitHub OAuth is not configured on this server. Set GITHUB_CLIENT_ID and
              GITHUB_CLIENT_SECRET in the backend environment, or use a demo profile
              below.
            </p>
          )}
        </section>

        <section
          className={`mt-12 ${wantsDemo ? "" : "border-t border-line pt-10"} ${githubUser ? "hidden" : ""}`}
        >
          <h2 className="text-[15px] font-semibold">
            {wantsDemo ? "Pick a demo profile" : "Or try a demo profile"}
          </h2>
          <p className="mb-5 mt-1.5 max-w-[58ch] text-[13.5px] leading-relaxed text-muted">
            Three prepared contributors against a fixed corpus of{" "}
            {health ? health.issues_in_corpus : "23"} issues. No GitHub account, no API
            key, no network.
          </p>
          <div className="grid gap-px overflow-hidden rounded-[10px] border border-line bg-line sm:grid-cols-3">
            {(health?.demo_profiles ?? ["alex", "priya", "rahul"]).map((name) => (
              <button
                key={name}
                onClick={() => startDemo(name)}
                disabled={busy !== null}
                className="group bg-surface p-4 text-left transition-colors hover:bg-surface-2 disabled:opacity-50"
              >
                <span className="flex items-center justify-between text-[14px] font-medium">
                  @{name}
                  <ArrowRight
                    size={14}
                    className="text-muted"
                  />
                </span>
                <span className="mt-1.5 block text-[13px] leading-relaxed text-muted">
                  {busy === name ? "Building skill graph..." : DEMO_BLURB[name] ?? ""}
                </span>
              </button>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={<div className="flex-1" />}>
      <OnboardingInner />
    </Suspense>
  );
}
