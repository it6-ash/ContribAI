import Link from "next/link";
import { Nav } from "@/components/Nav";

export const metadata = {
  title: "Terms — ContribAI",
  description: "What ContribAI does and does not promise.",
};

export default function Terms() {
  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-[72ch] flex-1 px-6 py-16">
        <h1 className="display-sm">Terms</h1>
        <p className="mt-3 font-mono text-[12px] text-muted">
          Last updated 20 September 2026
        </p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed text-muted">
          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              What this is
            </h2>
            <p>
              ContribAI ranks open-source issues against the evidence in your
              public GitHub history and explains its reasoning. It is a research
              and discovery aid, provided as-is, with no warranty.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              What the numbers are
            </h2>
            <p>
              Fit scores, readiness percentages, difficulty ratings and effort
              ranges are internal heuristics. They are not validated models and
              they are not predictions. An issue rated a strong match may still be
              wrong for you, already taken, or harder than it looks. Read the issue
              before committing time to it.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              Model-written text
            </h2>
            <p>
              Anything tagged{" "}
              <code className="font-mono text-foreground">ai-written</code> was
              produced by a language model from the GitHub data shown alongside it.
              It can be wrong. Text tagged{" "}
              <code className="font-mono text-foreground">rule-derived</code> comes
              from deterministic analysis and involves no model. Treat file paths,
              effort estimates and required skills as inferences to verify, not
              facts.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              Using GitHub through us
            </h2>
            <p>
              Your use of GitHub data remains subject to GitHub&rsquo;s own terms.
              Respect each project&rsquo;s contribution guidelines, licence and code
              of conduct. Do not use ContribAI to bulk-open pull requests, spam
              maintainers, or claim issues you do not intend to work on.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              Liability
            </h2>
            <p>
              The software is provided without warranty of any kind. The authors
              are not liable for time spent on an issue that turned out to be
              unsuitable, for a rejected pull request, or for anything arising from
              use of the recommendations.
            </p>
          </section>
        </div>

        <Link
          href="/"
          className="mt-12 inline-block text-[13.5px] text-accent underline underline-offset-4"
        >
          Back to ContribAI
        </Link>
      </main>
    </>
  );
}
