import Link from "next/link";
import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import { Nav } from "@/components/Nav";
import { CountUp, Reveal, WordReveal } from "@/components/motion";
import { PipelineScroll } from "@/components/PipelineScroll";
import { MatchSpaceLazy } from "@/components/MatchSpaceLazy";

const EVIDENCE = [
  ["Fact", "The repository contains CONTRIBUTING.md. Last commit 2 days ago. 48 contributors."],
  ["Inference", "This issue probably requires familiarity with SQLAlchemy query construction."],
  ["Estimate", "Roughly 3 to 6 hours, assuming the repository builds first try."],
] as const;

const DIMENSIONS: Array<[string, number]> = [
  ["Skill match", 0.92],
  ["Difficulty fit", 1.0],
  ["Issue clarity", 0.95],
  ["Repo accessibility", 0.95],
  ["Technology match", 0.8],
  ["Effort fit", 1.0],
];

export default function Home() {
  return (
    <>
      <Nav />

      <main className="mx-auto w-full max-w-[1400px] flex-1 px-6">
        {/* ── Hero ─────────────────────────────────────────────── */}
        <section className="grid items-center gap-14 pt-20 pb-28 lg:grid-cols-[1.04fr_0.96fr] lg:pt-24">
          <div>
            {/* No text-gradient here: WordReveal wraps each word in an
                overflow-hidden span, which breaks background-clip:text and
                renders the whole headline transparent. */}
            <WordReveal
              text="Find the issue that is actually right for you."
              className="display max-w-[13ch]"
            />
            <p className="mt-7 max-w-[50ch] text-[17px] leading-relaxed text-muted">
              ContribAI reads your GitHub evidence, analyses real issues, and builds a
              contribution path matched to your skills.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Link
                href="/onboarding"
                className="group inline-flex items-center gap-2 rounded-[10px] bg-accent px-6 py-3 text-[14.5px] font-medium text-on-accent transition-transform active:translate-y-px"
              >
                Get started
                <ArrowRight
                  size={15}
                  weight="bold"
                />
              </Link>
              <Link
                href="/onboarding?demo=1"
                className="inline-flex items-center rounded-[10px] border border-line px-6 py-3 text-[14.5px] font-medium transition-colors hover:border-muted/50"
              >
                Explore demo
              </Link>
            </div>
          </div>

          {/* The product's real output, at the shape it really has. */}
          <div data-tilt className="panel p-6 lg:p-7">
            <div className="flex items-start justify-between gap-6">
              <div className="min-w-0">
                <p className="font-mono text-[12px] text-muted">
                  ledgerly/ledgerly-api <span className="text-muted/60">#1842</span>
                </p>
                <p className="mt-2 text-[16px] font-semibold leading-snug">
                  Pagination returns wrong page offsets when a transaction filter is
                  applied
                </p>
              </div>
              <div className="shrink-0 text-right">
                <div className="font-mono text-[38px] leading-none tracking-tight text-accent">
                  <CountUp to={91} />
                  <span className="text-[16px] text-muted">%</span>
                </div>
                <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                  fit
                </div>
              </div>
            </div>

            <Reveal className="mt-7 space-y-2.5" stagger={0.05}>
              {DIMENSIONS.map(([label, v]) => (
                <div key={label} className="flex items-center gap-3">
                  <span className="w-36 shrink-0 text-[12.5px] text-muted">{label}</span>
                  <span className="h-1 flex-1 overflow-hidden rounded-full bg-white/[0.07]">
                    <span
                      className="block h-full rounded-full bg-accent"
                      style={{ width: `${v * 100}%` }}
                    />
                  </span>
                  <span className="w-9 shrink-0 text-right font-mono text-[11.5px] tnum text-muted">
                    {Math.round(v * 100)}
                  </span>
                </div>
              ))}
            </Reveal>

            <div className="mt-7 border-t border-line pt-5">
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
                likely file
              </p>
              <p className="mt-1.5 font-mono text-[12.5px] text-accent">
                src/ledgerly/services/transaction_service.py
              </p>
              <p className="mt-1 font-mono text-[11px] text-muted">named in the issue</p>
            </div>
          </div>
        </section>

        {/* ── The gap ──────────────────────────────────────────── */}
        <section data-depth className="border-t border-line py-24">
          <div className="grid gap-12 lg:grid-cols-[0.95fr_1.05fr]">
            <h2 className="display-sm max-w-[20ch] text-gradient">
              A label says an issue is beginner-friendly. It does not say it is right
              for you.
            </h2>
            <div>
              <p className="max-w-[62ch] text-[16px] leading-relaxed text-muted">
                GitHub already recommends repositories from your activity and stars. The
                gap sits one level below that: given <em>this</em> issue and{" "}
                <em>this</em> contributor, is it a realistic pull request, and what would
                it take? Answering needs both sides modelled.
              </p>

              <p className="mt-10 max-w-[56ch] text-[15px] leading-relaxed text-muted">
                Eight weighted dimensions decide the ranking, and{" "}
                <span className="font-mono text-foreground">
                  <CountUp to={0} />
                </span>{" "}
                model calls are involved in producing it. The language model only
                writes about a ranking it was handed.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* ── Pinned pipeline ────────────────────────────────────── */}
      <div className="mx-auto w-full max-w-[1400px] px-6">
        <PipelineScroll />
      </div>

      <main className="mx-auto w-full max-w-[1400px] px-6">
        {/* ── The model, as space ──────────────────────────────── */}
        <section data-depth className="border-t border-line py-24">
          <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:gap-14">
            <div>
              <h2 className="display-sm max-w-[16ch]">
                Fit is a distance, not a badge.
              </h2>
              <p className="mt-5 max-w-[46ch] text-[15px] leading-relaxed text-muted">
                Three of the eight scoring dimensions become axes here. You are at
                the centre, every issue sits where its scores put it, and the ones
                worth your time are the ones nearby.
              </p>
              <p className="mt-4 max-w-[46ch] text-[14px] leading-relaxed text-muted">
                A ranked list can tell you which issue came first. It cannot show
                you that two of them are neighbours and the third is nowhere near.
              </p>
              <p className="mt-6 font-mono text-[11.5px] text-muted">
                scroll to orbit, hover a point to read it
              </p>
            </div>
            <MatchSpaceLazy />
          </div>
        </section>

        {/* ── Evidence discipline ──────────────────────────────── */}
        <section data-depth className="border-t border-line py-24">
          <h2 className="display-sm max-w-[22ch] text-gradient">
            Facts and inferences never share a line.
          </h2>
          {/* Was three equal cards in a row, the reflex grid. This is a
              definition list, which is what the content actually is. */}
          <Reveal className="mt-10 divide-y divide-line border-y border-line">
            {EVIDENCE.map(([kind, line]) => (
              <div
                key={kind}
                className="grid gap-x-8 gap-y-2 py-5 md:grid-cols-[9rem_1fr]"
              >
                <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-accent">
                  {kind}
                </span>
                <p className="max-w-[62ch] text-[15px] leading-relaxed text-muted">
                  {line}
                </p>
              </div>
            ))}
          </Reveal>
          <p className="mt-8 max-w-[68ch] text-[15px] leading-relaxed text-muted">
            Model-written text is tagged <code className="text-foreground">ai-written</code>.
            Rule-derived text is tagged <code className="text-foreground">rule-derived</code>.
            You always know which one you are reading, and the rule-derived half keeps
            working when the model is unreachable.
          </p>
        </section>

        {/* ── Close ────────────────────────────────────────────── */}
        <section data-depth className="border-t border-line py-28">
          <h2 className="display max-w-[15ch] text-gradient">
            You do not need to know everything before you start.
          </h2>
          <p className="mt-7 max-w-[54ch] text-[17px] leading-relaxed text-muted">
            You need to know enough to start. ContribAI tells you which part that is.
          </p>
          <Link
            href="/onboarding"
            className="group mt-10 inline-flex items-center gap-2 rounded-[10px] bg-accent px-6 py-3 text-[14.5px] font-medium text-on-accent transition-transform active:translate-y-px"
          >
            Get started
            <ArrowRight
              size={15}
              weight="bold"
             
            />
          </Link>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-4 px-6 py-8">
          <p className="text-[13px] text-muted">
            Fit scores and effort estimates are internal heuristics, not guarantees.
          </p>
          <nav className="flex items-center gap-5 text-[13px]">
            <Link href="/privacy" className="text-muted hover:text-foreground">
              Privacy
            </Link>
            <Link href="/terms" className="text-muted hover:text-foreground">
              Terms
            </Link>
            <a
              href="https://github.com/it6-ash/ContribAI"
              className="text-muted hover:text-foreground"
              target="_blank"
              rel="noreferrer"
            >
              Source
            </a>
          </nav>
        </div>
      </footer>
    </>
  );
}
