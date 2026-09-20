import Link from "next/link";
import {
  ArrowRight,
  FileMagnifyingGlass,
  GitPullRequest,
  ListChecks,
  Path,
} from "@phosphor-icons/react/dist/ssr";
import { Nav } from "@/components/Nav";

const PIPELINE = [
  {
    icon: FileMagnifyingGlass,
    title: "Evidence, not self-assessment",
    body: "Your skill graph is built from repositories, dependency manifests, commit recency and merged pull requests. Every entry shows the evidence that produced it.",
  },
  {
    icon: ListChecks,
    title: "Issues read like an engineer would",
    body: "Each candidate issue gets a difficulty rating, an effort range, the concepts involved, and the files most likely to change, with the reasoning attached.",
  },
  {
    icon: Path,
    title: "A score that shows its work",
    body: "Eight weighted dimensions decide the ranking. It runs without a model call, so the same inputs always produce the same answer.",
  },
  {
    icon: GitPullRequest,
    title: "A path to the pull request",
    body: "Skill gaps with honest time estimates, then a step-by-step contribution plan with the commands, the expected result, and the mistake people usually make.",
  },
];

export default function Home() {
  return (
    <>
      <Nav />

      <main className="mx-auto w-full max-w-[1400px] flex-1 px-6">
        <section className="grid items-center gap-12 pt-20 pb-24 lg:grid-cols-[1.05fr_0.95fr] lg:pt-24">
          <div>
            <h1 className="max-w-[16ch] text-4xl font-semibold leading-[1.08] tracking-tight md:text-5xl lg:text-6xl">
              Find the open-source issue that is actually right for you.
            </h1>
            <p className="mt-6 max-w-[54ch] text-[16px] leading-relaxed text-muted">
              ContribAI reads your GitHub experience, analyses real issues, and builds a
              contribution path matched to your skills.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link
                href="/onboarding"
                className="inline-flex items-center gap-2 rounded-[10px] bg-accent px-5 py-2.5 text-[14px] font-medium text-[#06070a] transition-transform active:translate-y-px"
              >
                Get started
                <ArrowRight size={15} weight="bold" />
              </Link>
              <Link
                href="/onboarding?demo=1"
                className="inline-flex items-center rounded-[10px] border border-line px-5 py-2.5 text-[14px] font-medium transition-colors hover:border-muted/50"
              >
                Explore demo
              </Link>
            </div>
          </div>

          {/* The product's actual output, not a mocked screenshot: this is the
              real shape of a recommendation the engine produces. */}
          <div className="panel p-6 lg:p-7">
            <div className="flex items-start justify-between gap-6">
              <div>
                <p className="font-mono text-[12px] text-muted">
                  ledgerly/ledgerly-api <span className="text-muted/60">#1842</span>
                </p>
                <p className="mt-1.5 text-[15px] font-semibold leading-snug">
                  Pagination returns wrong page offsets when a transaction filter is
                  applied
                </p>
              </div>
              <div className="shrink-0 text-right">
                <div className="font-mono text-[30px] leading-none tracking-tight text-accent">
                  88<span className="text-[15px] text-muted">%</span>
                </div>
              </div>
            </div>

            <dl className="mt-6 space-y-2">
              {[
                ["Skill match", 0.92],
                ["Difficulty fit", 1.0],
                ["Issue clarity", 0.95],
                ["Repo accessibility", 0.95],
              ].map(([label, value]) => (
                <div key={label as string} className="flex items-center gap-3">
                  <dt className="w-36 shrink-0 text-[13px] text-muted">{label}</dt>
                  <dd className="h-1 flex-1 overflow-hidden rounded-full bg-line">
                    <span
                      className="block h-full rounded-full bg-accent"
                      style={{ width: `${(value as number) * 100}%` }}
                    />
                  </dd>
                </div>
              ))}
            </dl>

            <p className="mt-6 border-t border-line pt-5 font-mono text-[12px] leading-relaxed text-muted">
              likely file
              <br />
              <span className="text-foreground">
                src/ledgerly/services/transaction_service.py
              </span>
            </p>
          </div>
        </section>

        <section className="border-t border-line py-20">
          <h2 className="max-w-[24ch] text-2xl font-semibold tracking-tight md:text-3xl">
            A label tells you an issue is beginner-friendly. It does not tell you it is
            right for you.
          </h2>
          <p className="mt-5 max-w-[68ch] text-[15px] leading-relaxed text-muted">
            GitHub already recommends repositories based on your activity and stars. The
            gap is one level down: given this specific issue and this specific
            contributor, is this a realistic first pull request, and what would it take?
            That question needs both sides modelled.
          </p>

          <div className="mt-12 grid gap-px overflow-hidden rounded-[10px] border border-line bg-line sm:grid-cols-2">
            {PIPELINE.map(({ icon: Icon, title, body }) => (
              <div key={title} className="bg-surface p-6 lg:p-7">
                <Icon size={20} className="text-accent" />
                <h3 className="mt-4 text-[15px] font-semibold tracking-tight">{title}</h3>
                <p className="mt-2 max-w-[48ch] text-[14px] leading-relaxed text-muted">
                  {body}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-t border-line py-20">
          <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
            <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">
              Facts and inferences never share a line.
            </h2>
            <div className="space-y-5">
              {[
                [
                  "Fact",
                  "The repository contains CONTRIBUTING.md. Last commit 2 days ago. 48 contributors.",
                ],
                [
                  "Inference",
                  "This issue probably requires familiarity with SQLAlchemy query construction.",
                ],
                ["Estimate", "Roughly 3 to 6 hours, assuming the repository builds first try."],
              ].map(([kind, line]) => (
                <div key={kind} className="flex gap-4 border-b border-line pb-5 last:border-b-0">
                  <span className="w-20 shrink-0 font-mono text-[11px] uppercase tracking-[0.12em] text-accent">
                    {kind}
                  </span>
                  <span className="text-[14.5px] leading-relaxed text-muted">{line}</span>
                </div>
              ))}
              <p className="text-[14px] leading-relaxed text-muted">
                Anything the model wrote is marked as such. Anything derived from rules is
                reproducible without a model. You always know which one you are reading.
              </p>
            </div>
          </div>
        </section>

        <section className="border-t border-line py-20">
          <h2 className="max-w-[20ch] text-2xl font-semibold tracking-tight md:text-3xl">
            You do not need to know everything before you start.
          </h2>
          <p className="mt-4 max-w-[60ch] text-[15px] leading-relaxed text-muted">
            You need to know enough to start. ContribAI tells you which part that is.
          </p>
          <div className="mt-8">
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-2 rounded-[10px] bg-accent px-5 py-2.5 text-[14px] font-medium text-[#06070a] transition-transform active:translate-y-px"
            >
              Get started
              <ArrowRight size={15} weight="bold" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-4 px-6 py-8">
          <p className="text-[13px] text-muted">
            ContribAI. Fit scores and effort estimates are internal heuristics, not
            guarantees.
          </p>
          <a
            href="https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-open-source"
            className="text-[13px] text-muted hover:text-foreground"
            target="_blank"
            rel="noreferrer"
          >
            GitHub contribution guide
          </a>
        </div>
      </footer>
    </>
  );
}
