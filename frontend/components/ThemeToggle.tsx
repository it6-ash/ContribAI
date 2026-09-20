"use client";

import { useEffect, useState } from "react";
import { Desktop, Moon, Sun } from "@phosphor-icons/react/dist/ssr";

type Choice = "light" | "dark" | "system";
const KEY = "contribai-theme";

/** Applies the choice by stamping data-theme on <html>.
 *  "system" removes the stamp so the CSS media query takes over again. */
function apply(choice: Choice) {
  const root = document.documentElement;
  if (choice === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", choice);
}

const OPTIONS: Array<[Choice, typeof Sun, string]> = [
  ["light", Sun, "Light"],
  ["system", Desktop, "Match system"],
  ["dark", Moon, "Dark"],
];

export function ThemeToggle() {
  const [choice, setChoice] = useState<Choice>("system");

  useEffect(() => {
    const saved = localStorage.getItem(KEY) as Choice | null;
    if (saved === "light" || saved === "dark") {
      setChoice(saved);
      apply(saved);
    }
  }, []);

  function pick(next: Choice) {
    setChoice(next);
    apply(next);
    if (next === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, next);
  }

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className="flex items-center overflow-hidden rounded-full border border-line"
    >
      {OPTIONS.map(([value, Icon, label]) => (
        <button
          key={value}
          role="radio"
          aria-checked={choice === value}
          aria-label={label}
          title={label}
          onClick={() => pick(value)}
          className={`p-1.5 transition-colors ${
            choice === value
              ? "bg-accent text-on-accent"
              : "text-muted hover:text-foreground"
          }`}
        >
          <Icon size={13} weight={choice === value ? "fill" : "regular"} />
        </button>
      ))}
    </div>
  );
}

/** Runs before first paint so a saved light choice does not flash dark.
 *  Inlined in <head>; keep it tiny and dependency-free. */
export const themeScript = `(function(){try{var t=localStorage.getItem("${KEY}");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;
