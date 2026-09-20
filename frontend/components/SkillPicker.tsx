"use client";

import { useMemo, useRef, useState } from "react";
import { MagnifyingGlass, Plus, X } from "@phosphor-icons/react/dist/ssr";
import type { Level, Taxonomy } from "@/lib/types";

export interface PickedSkill {
  name: string;
  level: Level;
}

// Order and membership come from /api/taxonomy; this is only the short label.
const LEVEL_SHORT: Record<Level, string> = {
  novice: "Nov",
  beginner: "Beg",
  intermediate: "Int",
  advanced: "Adv",
  expert: "Exp",
};

const CATEGORY_LABEL: Record<string, string> = {
  language: "Languages",
  framework: "Frameworks",
  infrastructure: "Infrastructure",
  data: "Data",
  engineering: "Engineering",
  ai: "AI",
};

export function SkillPicker({
  taxonomy,
  picked,
  onChange,
}: {
  taxonomy: Taxonomy | null;
  picked: PickedSkill[];
  onChange: (next: PickedSkill[]) => void;
}) {
  const [query, setQuery] = useState("");
  const levels: Level[] = taxonomy?.skill_levels ?? [
    "novice",
    "beginner",
    "intermediate",
    "advanced",
    "expert",
  ];
  const inputRef = useRef<HTMLInputElement>(null);

  const all = useMemo(
    () =>
      Object.entries(taxonomy?.skills ?? {}).flatMap(([category, names]) =>
        names.map((name) => ({ name, category })),
      ),
    [taxonomy],
  );

  const q = query.trim().toLowerCase();
  const matches = q ? all.filter((s) => s.name.toLowerCase().includes(q)) : all;

  const isPicked = (name: string) =>
    picked.some((p) => p.name.toLowerCase() === name.toLowerCase());

  function toggle(name: string) {
    onChange(
      isPicked(name)
        ? picked.filter((p) => p.name.toLowerCase() !== name.toLowerCase())
        : [...picked, { name, level: "intermediate" as Level }],
    );
  }

  function setLevel(name: string, level: Level) {
    onChange(picked.map((p) => (p.name === name ? { ...p, level } : p)));
  }

  // Anything typed that is not in the taxonomy is still worth keeping: the
  // backend stores it as a custom skill rather than discarding it.
  const exactExists = all.some((s) => s.name.toLowerCase() === q);
  const canAddCustom = q.length >= 2 && !exactExists && !isPicked(query.trim());

  function addCustom() {
    const name = query.trim();
    if (!name || isPicked(name)) return;
    onChange([...picked, { name, level: "intermediate" }]);
    setQuery("");
    inputRef.current?.focus();
  }

  const grouped = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const s of matches) (out[s.category] ??= []).push(s.name);
    return out;
  }, [matches]);

  return (
    <div>
      {/* Selected first, with a level each. Buried at the bottom nobody would
          notice that a level control existed at all. */}
      {picked.length ? (
        <div className="panel mb-4 p-4">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h3 className="text-[13px] font-medium">
              Your skills{" "}
              <span className="font-mono text-[11.5px] text-muted">
                {picked.length}
              </span>
            </h3>
            <button
              onClick={() => onChange([])}
              className="text-[12px] text-muted underline underline-offset-4 hover:text-foreground"
            >
              clear all
            </button>
          </div>

          <ul className="space-y-1.5">
            {picked.map((p) => (
              <li
                key={p.name}
                className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-[8px] border border-line bg-surface-2 px-3 py-2"
              >
                <span className="min-w-0 flex-1 truncate font-mono text-[12.5px]">
                  {p.name}
                </span>

                <div
                  role="radiogroup"
                  aria-label={`Level for ${p.name}`}
                  className="flex overflow-hidden rounded-[6px] border border-line"
                >
                  {levels.map((lvl) => (
                    <button
                      key={lvl}
                      role="radio"
                      aria-checked={p.level === lvl}
                      title={lvl}
                      onClick={() => setLevel(p.name, lvl)}
                      className={`px-2.5 py-1 font-mono text-[11px] transition-colors ${
                        p.level === lvl
                          ? "bg-accent text-on-accent"
                          : "text-muted hover:text-foreground"
                      }`}
                    >
                      {LEVEL_SHORT[lvl]}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => toggle(p.name)}
                  aria-label={`Remove ${p.name}`}
                  className="text-muted hover:text-foreground"
                >
                  <X size={13} />
                </button>
              </li>
            ))}
          </ul>

          <p className="mt-3 text-[11.5px] leading-relaxed text-muted">
            Self-reported levels sit below anything your GitHub history proves, so
            claiming advanced never outranks demonstrated work.
          </p>
        </div>
      ) : null}

      <div className="relative">
        <MagnifyingGlass
          size={14}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (canAddCustom) addCustom();
              else if (matches.length === 1) toggle(matches[0].name);
            }
          }}
          placeholder="Search skills, or type your own and press Enter"
          aria-label="Search or add a skill"
          className="w-full rounded-[10px] border border-line bg-surface py-2.5 pl-9 pr-3 text-[13.5px] placeholder:text-muted/70 focus:border-accent focus:outline-none"
        />
      </div>

      {canAddCustom ? (
        <button
          onClick={addCustom}
          className="mt-2 inline-flex items-center gap-1.5 rounded-[8px] border border-accent/40 bg-accent/10 px-3 py-1.5 text-[12.5px] text-accent"
        >
          <Plus size={12} weight="bold" />
          Add &ldquo;{query.trim()}&rdquo;
        </button>
      ) : null}

      <div className="mt-5 space-y-4">
        {Object.keys(grouped).length === 0 ? (
          <p className="text-[13px] text-muted">
            No built-in skill matches &ldquo;{query}&rdquo;. Press Enter to add it as
            your own.
          </p>
        ) : null}

        {Object.entries(grouped).map(([category, names]) => (
          <section key={category}>
            <h4 className="mb-2 font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
              {CATEGORY_LABEL[category] ?? category}
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {names.map((name) => {
                const on = isPicked(name);
                return (
                  <button
                    key={name}
                    onClick={() => toggle(name)}
                    aria-pressed={on}
                    className={`rounded border px-2 py-1 font-mono text-[11.5px] transition-colors ${
                      on
                        ? "border-accent/50 bg-accent/10 text-accent"
                        : "border-line text-muted hover:border-muted/50 hover:text-foreground"
                    }`}
                  >
                    {name}
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
