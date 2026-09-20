"use client";

import { useState } from "react";
import { Check, Copy, Warning } from "@phosphor-icons/react/dist/ssr";
import type { Plan } from "@/lib/types";
import { SourceTag } from "./primitives";

function CommandLine({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);

  return (
    <div className="mt-2 flex items-center gap-2 rounded border border-line bg-background px-3 py-2">
      <span className="select-none font-mono text-[12px] text-muted">$</span>
      <code className="flex-1 overflow-x-auto whitespace-pre font-mono text-[12.5px]">
        {command}
      </code>
      <button
        onClick={() => {
          navigator.clipboard.writeText(command);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
        className="shrink-0 text-muted hover:text-foreground"
        aria-label={copied ? "Copied" : "Copy command"}
      >
        {copied ? <Check size={14} className="text-ok" /> : <Copy size={14} />}
      </button>
    </div>
  );
}

export function ContributionRoadmap({ plan }: { plan: Plan }) {
  const [done, setDone] = useState<Set<number>>(new Set());

  const toggle = (i: number) =>
    setDone((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <div>
      <div className="mb-5 flex items-center justify-between gap-4">
        <p className="font-mono text-[12px] text-muted">
          {done.size}/{plan.steps.length} complete
        </p>
        <SourceTag source={plan.source} />
      </div>

      {plan.prerequisites.length ? (
        <div className="panel-2 mb-6 p-4">
          <h3 className="mb-2 text-[13.5px] font-semibold">Before you start</h3>
          <ul className="space-y-1">
            {plan.prerequisites.map((p) => (
              <li key={p} className="flex gap-2 text-[13px] leading-relaxed text-muted">
                <span className="text-warn">△</span>
                {p}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <ol className="space-y-0">
        {plan.steps.map((step, i) => {
          const isDone = done.has(i);
          return (
            <li key={step.title} className="border-b border-line py-4 last:border-b-0">
              <div className="flex items-start gap-3">
                <button
                  onClick={() => toggle(i)}
                  aria-pressed={isDone}
                  className={`mt-0.5 flex size-5 shrink-0 items-center justify-center rounded border font-mono text-[10px] transition-colors ${
                    isDone
                      ? "border-ok bg-ok/15 text-ok"
                      : "border-line text-muted hover:border-muted"
                  }`}
                  aria-label={`Mark step ${i + 1} ${isDone ? "incomplete" : "complete"}`}
                >
                  {isDone ? <Check size={12} weight="bold" /> : i + 1}
                </button>

                <div className="min-w-0 flex-1">
                  <h4
                    className={`text-[14px] font-medium ${isDone ? "text-muted line-through" : ""}`}
                  >
                    {step.title}
                  </h4>
                  {step.objective ? (
                    <p className="mt-1 max-w-[70ch] text-[13.5px] leading-relaxed text-muted">
                      {step.objective}
                    </p>
                  ) : null}
                  {step.command ? <CommandLine command={step.command} /> : null}
                  {step.expected ? (
                    <p className="mt-2 text-[12.5px] text-muted">
                      <span className="text-ok">Expect:</span> {step.expected}
                    </p>
                  ) : null}
                  {step.common_failure ? (
                    <p className="mt-1 flex gap-1.5 text-[12.5px] text-muted">
                      <Warning size={13} className="mt-0.5 shrink-0 text-warn" />
                      {step.common_failure}
                    </p>
                  ) : null}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
