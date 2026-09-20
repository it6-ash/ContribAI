"use client";

import { useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { reduced } from "./motion";

gsap.registerPlugin(ScrollTrigger, useGSAP);

/** The four matching stages, walked through under the reader's scroll.
 *
 *  Motivated by storytelling: the product's whole argument is that ranking
 *  happens in a defensible order, and a static list of four bullets cannot
 *  show a funnel narrowing. Pinning holds the diagram still while the numbers
 *  actually fall, so the narrowing is the animation rather than a claim.
 */
const STAGES = [
  {
    n: "01",
    name: "Hard filters",
    left: 2400,
    right: 1180,
    body: "Assigned, closed, already has a pull request, wontfix, security-labelled, inactive repository, outside your stack. Deterministic, and it reports what it dropped and why.",
  },
  {
    n: "02",
    name: "Retrieval",
    left: 1180,
    right: 240,
    body: "TF-IDF cosine between your profile and every surviving issue. Exact, offline, and instant at this corpus size. No embedding API in the path.",
  },
  {
    n: "03",
    name: "Scoring",
    left: 240,
    right: 48,
    body: "Eight weighted dimensions. Runs without a model call, so the same inputs always produce the same ranking and you can inspect every number behind it.",
  },
  {
    n: "04",
    name: "Reasoning",
    left: 48,
    right: 6,
    body: "Only now does a language model write. It explains the ranking it was handed. It never changes a score, and it never invents a GitHub fact.",
  },
];

export function PipelineScroll() {
  const root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);
  // Animated layout stacks the four narrations in one cell. Reduced motion
  // gets a plain vertical list instead: hiding three of them with no way to
  // reveal them would make the content unreachable, which an earlier version
  // of this component actually did.
  const [animated, setAnimated] = useState(false);

  useGSAP(
    () => {
      if (reduced()) return;
      setAnimated(true);

      // Hidden state is set here, not in CSS, so a visitor with JS disabled or
      // motion reduced never lands on permanently-invisible text.
      gsap.set('[data-stage]:not([data-stage="0"])', { opacity: 0, y: 24 });
      gsap.set("[data-bar]", { scaleX: 0 });

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: root.current,
          start: "top top", // pin the moment the section reaches the top
          end: "+=2600",
          pin: true,
          scrub: 0.8,
          onUpdate: (self) =>
            setActive(Math.min(STAGES.length - 1, Math.floor(self.progress * STAGES.length))),
        },
      });

      STAGES.forEach((_, i) => {
        // The narration blocks are stacked in the same grid cell, so an
        // outgoing stage must reach opacity 0. Leaving it part-visible makes
        // four paragraphs overprint each other.
        tl.to(`[data-stage="${i}"]`, { opacity: 1, y: 0, duration: 0.8 }, i)
          .to(`[data-bar="${i}"]`, { scaleX: 1, duration: 0.8 }, i);
        if (i < STAGES.length - 1) {
          tl.to(`[data-stage="${i}"]`, { opacity: 0, y: -18, duration: 0.5 }, i + 0.8);
        }
      });
    },
    { scope: root },
  );

  return (
    <section
      ref={root}
      className="relative flex min-h-[100dvh] flex-col justify-center overflow-hidden py-20"
    >
      <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-muted">
        How a recommendation is made
      </p>
      <h2 className="display-sm max-w-[18ch] text-gradient">
        Four stages. Three of them need no model at all.
      </h2>

      <div className="mt-12 grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:gap-16">
        {/* Left: the funnel narrowing */}
        <div className="space-y-3">
          {STAGES.map((s, i) => (
            <div
              key={s.n}
              data-bar-row
              className={`rounded-[10px] border p-4 transition-colors duration-300 ${
                active === i
                  ? "border-accent/40 bg-accent/[0.06]"
                  : "border-line bg-surface/50"
              }`}
            >
              <div className="flex items-baseline justify-between gap-4">
                <span className="font-mono text-[11.5px] text-muted">
                  {s.n} {s.name}
                </span>
                <span className="font-mono text-[12px] tnum text-muted">
                  {s.left.toLocaleString()} → {s.right.toLocaleString()}
                </span>
              </div>
              <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-[var(--viz-empty,#1b2030)]">
                <div
                  data-bar={i}
                  className="h-full origin-left rounded-full bg-accent"
                  style={{ width: `${(s.right / s.left) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Right: the narration for whichever stage is current */}
        <div className={animated ? "relative min-h-[260px]" : "space-y-10"}>
          {STAGES.map((s, i) => (
            <div
              key={s.n}
              data-stage={i}
              className={animated ? "absolute inset-0" : ""}
            >
              <span className="font-mono text-[52px] leading-none text-accent/25">
                {s.n}
              </span>
              <h3 className="mt-3 text-[22px] font-semibold tracking-tight">{s.name}</h3>
              <p className="mt-4 max-w-[46ch] text-[15px] leading-relaxed text-muted">
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
