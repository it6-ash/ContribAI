"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { RefreshStatus } from "@/lib/types";

/** Poll fast while work is happening, slowly otherwise.
 *  A 3s poll when nothing is running would be pure noise; a 45s poll during a
 *  run would make the progress readout useless. */
const BUSY_MS = 3_000;
const IDLE_MS = 45_000;

/** Keeps the dashboard in step with the corpus.
 *
 *  The scheduler can finish a run at any moment, including one this tab did not
 *  start, so the page watches `runs_completed` rather than diffing timestamps:
 *  a run that begins and ends between two polls still bumps the counter, and is
 *  therefore never missed.
 */
export function useLiveCorpus(onNewData: () => void) {
  const [status, setStatus] = useState<RefreshStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastRuns = useRef<number | null>(null);
  const onNewDataRef = useRef(onNewData);
  onNewDataRef.current = onNewData;

  const poll = useCallback(async () => {
    try {
      const next = await api.refreshStatus();
      setStatus(next);
      if (lastRuns.current !== null && next.runs_completed > lastRuns.current) {
        onNewDataRef.current();
      }
      lastRuns.current = next.runs_completed;
      return next;
    } catch {
      return null; // a failed poll is not worth surfacing; the next one retries
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      const next = await poll();
      if (cancelled) return;
      // Stop polling entirely when the tab is hidden: a background tab does
      // not need live data and should not keep the server busy.
      const hidden = typeof document !== "undefined" && document.hidden;
      const delay = hidden ? IDLE_MS * 4 : next?.in_progress ? BUSY_MS : IDLE_MS;
      timer = setTimeout(tick, delay);
    };
    tick();

    const onVisible = () => {
      if (!document.hidden) poll();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [poll]);

  const refresh = useCallback(async () => {
    setStarting(true);
    setError(null);
    try {
      const res = await api.refreshCorpus();
      if (!res.started) setError(res.reason ?? "A refresh is already running.");
      await poll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start a refresh.");
    } finally {
      setStarting(false);
    }
  }, [poll]);

  return { status, refresh, starting, error, busy: !!status?.in_progress };
}
