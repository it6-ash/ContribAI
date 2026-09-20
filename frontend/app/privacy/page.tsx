import Link from "next/link";
import { Nav } from "@/components/Nav";

export const metadata = {
  title: "Privacy — ContribAI",
  description: "What ContribAI stores, why, and how to remove it.",
};

/** Written against what the code actually does. Every claim below is checkable
 *  in the repository, and nothing here describes a practice we do not follow. */
export default function Privacy() {
  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-[72ch] flex-1 px-6 py-16">
        <h1 className="display-sm">Privacy</h1>
        <p className="mt-3 font-mono text-[12px] text-muted">
          Last updated 20 September 2026
        </p>

        <div className="mt-10 space-y-8 text-[15px] leading-relaxed text-muted">
          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              What we store
            </h2>
            <p>
              If you sign in with GitHub we store your public GitHub id, username,
              avatar URL and bio, plus the skill graph we derive from your public
              repositories: languages, dependency manifests, topics, commit recency
              and merged pull requests. We also store the preferences you set, any
              skills you add yourself, and the issue recommendations generated for
              you.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              Your GitHub token
            </h2>
            <p>
              The OAuth access token is encrypted at rest and never leaves the
              server. It is not present in any API response, and your browser only
              ever holds a signed session id in an HttpOnly cookie. We request the{" "}
              <code className="font-mono text-foreground">read:user</code> scope
              only, which grants read access to your public profile and no access
              to your repositories.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              What we send elsewhere
            </h2>
            <p>
              Issue text, repository metadata and your skill names are sent to Groq
              to generate explanations and contribution plans. Your GitHub token is
              never included. If no model provider is configured the product falls
              back to rule-derived analysis and sends nothing to a third party.
            </p>
            <p className="mt-3">
              We query the GitHub API on your behalf to discover and re-check
              issues. We do not sell data, run advertising, or use third-party
              analytics.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              Removing your data
            </h2>
            <p>
              Signing out clears your session. To delete the stored profile, skill
              graph and recommendations, open an issue on{" "}
              <a
                href="https://github.com/it6-ash/ContribAI"
                className="text-accent underline underline-offset-4"
                target="_blank"
                rel="noreferrer"
              >
                the repository
              </a>{" "}
              or remove the app from your GitHub authorised applications, which
              invalidates the stored token immediately.
            </p>
          </section>

          <section>
            <h2 className="mb-2 text-[15px] font-semibold text-foreground">
              This is a project, not a company
            </h2>
            <p>
              ContribAI is open source and self-hostable. If you are running your
              own instance, you are the data controller for it and this page
              describes only the behaviour of the code, not any hosted service.
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
