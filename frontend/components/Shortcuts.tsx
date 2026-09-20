"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export interface Shortcut {
  keys: string[];
  label: string;
  run: () => void;
}

/** True when the user is typing, so a shortcut never steals a keystroke from
 *  an input, a textarea, or a contenteditable surface. */
function typing(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    el.isContentEditable
  );
}

/** Single-key shortcuts for the things a returning user does constantly.
 *
 *  Deliberately single-key rather than chorded: this is a tool people open
 *  daily to triage a list, and Ctrl+Shift+anything is not muscle memory. The
 *  typing guard is what makes that safe.
 */
export function useShortcuts(shortcuts: Shortcut[], enabled = true) {
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (typing(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === "?") {
        e.preventDefault();
        setHelpOpen((v) => !v);
        return;
      }
      if (e.key === "Escape" && helpOpen) {
        setHelpOpen(false);
        return;
      }
      const hit = shortcuts.find((s) => s.keys.includes(e.key));
      if (hit) {
        e.preventDefault();
        hit.run();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [shortcuts, enabled, helpOpen]);

  return { helpOpen, setHelpOpen };
}

export function ShortcutHelp({
  shortcuts,
  open,
  onClose,
}: {
  shortcuts: Shortcut[];
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const dismiss = useCallback(() => onClose(), [onClose]);
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      onClick={dismiss}
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 p-6"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="panel floating w-full max-w-[380px] p-5"
      >
        <h2 className="text-[14px] font-semibold">Keyboard</h2>
        <dl className="mt-4 space-y-2">
          {[...shortcuts, { keys: ["?"], label: "Show this", run: () => {} }].map(
            (s) => (
              <div key={s.label} className="flex items-center justify-between gap-6">
                <dt className="text-[13.5px] text-muted">{s.label}</dt>
                <dd className="flex gap-1">
                  {s.keys.map((k) => (
                    <kbd
                      key={k}
                      className="rounded border border-line bg-surface-2 px-1.5 py-0.5 font-mono text-[11px]"
                    >
                      {k === " " ? "space" : k}
                    </kbd>
                  ))}
                </dd>
              </div>
            ),
          )}
        </dl>
        <button
          onClick={dismiss}
          className="mt-5 text-[13px] text-accent underline underline-offset-4"
        >
          Close
        </button>
      </div>
    </div>
  );
}
