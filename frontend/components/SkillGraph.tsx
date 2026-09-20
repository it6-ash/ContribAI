"use client";

import { useState } from "react";
import { CaretDown } from "@phosphor-icons/react/dist/ssr";
import type { Skill } from "@/lib/types";

const CATEGORY_LABEL: Record<string, string> = {
  language: "Languages",
  framework: "Frameworks",
  infrastructure: "Infrastructure",
  data: "Data",
  engineering: "Engineering",
  ai: "AI",
};

const ORDER = ["language", "framework", "data", "infrastructure", "engineering", "ai"];

function SkillRow({ skill, index }: { skill: Skill; index: number }) {
  const [open, setOpen] = useState(false);
  const hasEvidence = skill.evidence.length > 0;

  return (
    <div className="reveal border-b border-line last:border-b-0" style={{ "--i": index } as React.CSSProperties}>
      <button
        onClick={() => hasEvidence && setOpen((v) => !v)}
        aria-expanded={hasEvidence ? open : undefined}
        className="flex w-full items-center gap-3 py-2 text-left"
        disabled={!hasEvidence}
      >
        <span className="w-32 shrink-0 truncate text-[13px]">{skill.name}</span>
        <span className="h-1 flex-1 overflow-hidden rounded-full bg-line">
          <span
            className="bar-fill block h-full rounded-full bg-accent"
            style={{ width: `${skill.confidence * 100}%` }}
          />
        </span>
        <span className="w-24 shrink-0 text-right font-mono text-[11px] text-muted">
          {skill.level}
        </span>
        {hasEvidence ? (
          <CaretDown
            size={12}
            className={`shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`}
          />
        ) : (
          <span className="w-3 shrink-0" />
        )}
      </button>
      {open ? (
        <ul className="pb-3 pl-2 text-[12.5px] leading-relaxed text-muted">
          {skill.evidence.map((item) => (
            <li key={item} className="flex gap-2">
              <span className="text-accent">/</span>
              <span>{item}</span>
            </li>
          ))}
          {skill.source === "self_reported" ? (
            <li className="mt-1 font-mono text-[11px] text-muted/70">
              self-reported, not verified against GitHub
            </li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}

export function SkillGraph({
  skillsByCategory,
}: {
  skillsByCategory: Record<string, Skill[]>;
}) {
  const categories = ORDER.filter((c) => skillsByCategory[c]?.length);
  let cursor = 0;

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {categories.map((category) => (
        <section key={category}>
          <h3 className="mb-1 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
            {CATEGORY_LABEL[category] ?? category}
          </h3>
          <div>
            {skillsByCategory[category].map((skill) => (
              <SkillRow key={skill.name} skill={skill} index={cursor++} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
