"use client";

import { useRef, useState } from "react";
import { PaperPlaneRight } from "@phosphor-icons/react/dist/ssr";
import { api, ApiError } from "@/lib/api";
import { Skeleton, SourceTag } from "./primitives";

const SUGGESTED = [
  "Which file should I read first?",
  "How do I reproduce this?",
  "What should I understand before coding?",
  "What skill am I missing here?",
];

interface Turn {
  question: string;
  answer: string | null;
  source?: string;
  error?: string;
}

export function AskAI({ issueId }: { issueId: number }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    setValue("");
    setBusy(true);
    setTurns((prev) => [...prev, { question: trimmed, answer: null }]);

    try {
      const res = await api.chat(issueId, trimmed);
      setTurns((prev) =>
        prev.map((t, i) =>
          i === prev.length - 1 ? { ...t, answer: res.answer, source: res.source } : t,
        ),
      );
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Something went wrong.";
      setTurns((prev) =>
        prev.map((t, i) =>
          i === prev.length - 1 ? { ...t, answer: "", error: message } : t,
        ),
      );
    } finally {
      setBusy(false);
      requestAnimationFrame(() =>
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight }),
      );
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={logRef} className="scroll-thin min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        {turns.length === 0 ? (
          <div>
            <p className="text-[13.5px] leading-relaxed text-muted">
              Ask about this issue and repository. Answers are grounded in the issue
              body, labels and repository tree. The assistant will not write the patch
              for you.
            </p>
            <div className="mt-4 space-y-1.5">
              {SUGGESTED.map((q) => (
                <button
                  key={q}
                  onClick={() => ask(q)}
                  className="block w-full rounded border border-line px-3 py-2 text-left text-[13px] text-muted transition-colors hover:border-muted/50 hover:text-foreground"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {turns.map((turn, i) => (
          <div key={i}>
            <p className="text-[13.5px] font-medium">{turn.question}</p>
            {turn.answer === null ? (
              <div className="mt-2 space-y-1.5">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-[88%]" />
                <Skeleton className="h-3 w-[64%]" />
              </div>
            ) : turn.error ? (
              <p className="mt-2 text-[13px] text-hard">{turn.error}</p>
            ) : (
              <>
                <p className="mt-2 whitespace-pre-wrap text-[13.5px] leading-relaxed text-muted">
                  {turn.answer}
                </p>
                {turn.source ? (
                  <div className="mt-1.5">
                    <SourceTag source={turn.source} />
                  </div>
                ) : null}
              </>
            )}
          </div>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(value);
        }}
        className="mt-4 flex items-center gap-2 border-t border-line pt-4"
      >
        <label htmlFor="ask-ai" className="sr-only">
          Ask about this issue
        </label>
        <input
          id="ask-ai"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask about this issue"
          disabled={busy}
          className="min-w-0 flex-1 rounded-[10px] border border-line bg-background px-3 py-2 text-[13.5px] text-foreground placeholder:text-muted/70 focus:border-accent focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy || !value.trim()}
          className="shrink-0 rounded-[10px] bg-accent p-2 text-[#06070a] transition-opacity disabled:opacity-40"
          aria-label="Send question"
        >
          <PaperPlaneRight size={15} weight="bold" />
        </button>
      </form>
    </div>
  );
}
