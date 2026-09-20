"use client";

import { useRouter } from "next/navigation";
import type { Recommendation } from "@/lib/types";
import { SCORE_DOMAIN, SEQ, seqStep, useTooltip } from "./viz";

/** Every recommendation against every scoring dimension, at once.
 *
 *  A stack of cards can only be read one at a time, so "which of these is
 *  strong on clarity but weak on skills?" takes six scrolls. A grid of
 *  magnitude is a heatmap, and it answers that in one look.
 *
 *  Sequential ramp, one hue: these cells are all the same measure (0-1), so
 *  identity colour would be wrong here.
 */
// Abbreviated headers ("Diff", "Access", "Learn") were unreadable: nothing on
// the page said what they meant. Each column now states its question.
const DIMENSIONS: Array<[key: string, short: string, full: string]> = [
  ["skill_match", "Skills", "Do you already have the skills this needs?"],
  ["difficulty_match", "Level", "Is the difficulty right for your experience?"],
  ["technology_match", "Stack", "Is it built with technologies you use?"],
  ["repository_accessibility", "Welcoming", "Does the project help newcomers contribute?"],
  ["issue_clarity", "Clarity", "Is the issue clearly described?"],
  ["effort_fit", "Time", "Does the effort fit what you have?"],
  ["learning_value", "Learning", "Would you learn something worthwhile?"],
  ["repository_activity", "Alive", "Is the repository actively maintained?"],
];

export function MatchHeatmap({ recs }: { recs: Recommendation[] }) {
  const router = useRouter();
  const { show, hide, node } = useTooltip();
  if (recs.length < 2) return null; // a one-row heatmap is just a bar chart

  return (
    <div className="viz panel overflow-hidden">
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-line px-5 py-3.5">
        <h3 className="text-[13.5px] font-medium">
          Compare every match, side by side
        </h3>
        <div className="flex items-center gap-2 font-mono text-[11px] text-muted">
          <span>{Math.round(SCORE_DOMAIN[0] * 100)}</span>
          <span className="flex gap-[2px]">
            {SEQ.map((c) => (
              <span key={c} className="size-3 rounded-[2px]" style={{ background: c }} />
            ))}
          </span>
          <span>{Math.round(SCORE_DOMAIN[1] * 100)}</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse">
          <caption className="sr-only">
            Scoring dimensions for each recommended issue, 0 to 100 percent.
          </caption>
          <thead>
            <tr>
              <th scope="col" className="w-[240px] px-5 py-2 text-left">
                <span className="sr-only">Issue</span>
              </th>
              {DIMENSIONS.map(([key, short, full]) => (
                <th
                  key={key}
                  scope="col"
                  title={full}
                  className="px-1 pb-2 text-center text-[11px] font-normal text-muted"
                >
                  {short}
                </th>
              ))}
              <th
                scope="col"
                className="px-4 pb-2 text-right font-mono text-[10.5px] font-normal text-muted"
              >
                Fit
              </th>
            </tr>
          </thead>
          <tbody>
            {recs.map((rec) => (
              <tr
                key={rec.issue.id}
                tabIndex={0}
                role="link"
                onClick={() => router.push(`/issues/${rec.issue.id}`)}
                onKeyDown={(e) =>
                  e.key === "Enter" && router.push(`/issues/${rec.issue.id}`)
                }
                className="cursor-pointer transition-colors hover:bg-surface-2"
              >
                <th scope="row" className="max-w-[260px] px-5 py-2 text-left font-normal">
                  <span className="line-clamp-2 block text-[12.5px] leading-snug">
                    {rec.issue.title}
                  </span>
                  <span className="block truncate font-mono text-[10.5px] text-muted">
                    {rec.issue.repository.full_name}#{rec.issue.number}
                  </span>
                </th>

                {DIMENSIONS.map(([key, , full]) => {
                  const v = rec.dimensions[key] ?? 0;
                  return (
                    <td key={key} className="px-[2px] py-[2px]">
                      {/* 2px gaps in the surface colour separate the cells. */}
                      <div
                        className="h-8 w-full rounded-[3px] transition-transform hover:scale-[1.06]"
                        style={{ background: seqStep(v, ...SCORE_DOMAIN) }}
                        onMouseMove={(e) =>
                          show(
                            e,
                            <>
                              <p className="font-medium">{full}</p>
                              <p className="font-mono text-muted">
                                {Math.round(v * 100)}%
                              </p>
                              <p className="mt-1 truncate text-muted">
                                {rec.issue.repository.full_name}#{rec.issue.number}
                              </p>
                            </>,
                          )
                        }
                        onMouseLeave={hide}
                      />
                    </td>
                  );
                })}

                <td className="px-4 text-right font-mono text-[12.5px] tabular-nums">
                  {Math.round(rec.fit_score * 100)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="border-t border-line px-5 py-2.5 text-[11.5px] text-muted">
        Darker means stronger. Hover any square for the exact score, or click a row
        to open the issue.
      </p>
    </div>
  );
}
