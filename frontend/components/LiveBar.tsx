"use client";

import { useEffect, useState } from "react";
import { ArrowClockwise, CircleNotch } from "@phosphor-icons/react/dist/ssr";
import type { RefreshStatus } from "@/lib/types";

/** "4 minutes ago", recomputed on a timer.
 *  Rendered client-side only: formatting a relative time on the server
 *  produces a value that is already wrong by the time it reaches the browser,
 *  and mismatches on hydration. */
function Ago({ iso }: { iso: string | null }) {
  const [, force] = useState(0);
  useEffect(() => {
    const t = setInterval(() => force((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, []);
  if (!iso) return <>never</>;

  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return <>just now</>;
  const mins = Math.round(secs / 60);
  if (mins < 60) return <>{mins}m ago</>;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return <>{hrs}h ago</>;
  return <>{Math.round(hrs / 24)}d ago</>;
}

export function LiveBar({
  status,
  busy,
  starting,
  error,
  onRefresh,
}: {
  status: RefreshStatus | null;
  busy: boolean;
  starting: boolean;
  error: string | null;
  onRefresh: () => void;
}) {
  const disabled = busy || starting || status?.can_refresh === false;
  const result = status?.last_result;

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <button
        onClick={onRefresh}
        disabled={disabled}
        title={
          status?.can_refresh === false
            ? "Set GITHUB_TOKEN on the server to search GitHub"
            : "Search GitHub for issues matching your skills"
        }
        className="inline-flex items-center gap-2 rounded-[10px] border border-line bg-surface px-3.5 py-2 text-[13.5px] font-medium transition-colors hover:border-muted/50 disabled:cursor-not-allowed disabled:opacity-55"
      >
        {busy || starting ? (
          <CircleNotch size={14} className="animate-spin" />
        ) : (
          <ArrowClockwise size={14} />
        )}
        {busy ? "Searching GitHub" : starting ? "Starting" : "Refresh"}
      </button>

      <span className="font-mono text-[11.5px] text-muted">
        {busy ? (
          // A run takes tens of seconds; saying so beats a spinner that looks stuck.
          <span className="text-accent">
            searching GitHub, results appear here automatically
          </span>
        ) : (
          <>
            updated <Ago iso={status?.last_run_at ?? null} />
            {result?.ingested !== undefined ? ` · +${result.ingested} issues` : ""}
            {result?.rate_limited ? " · rate limited, will retry" : ""}
          </>
        )}
      </span>

      {status?.enabled ? (
        <span className="font-mono text-[11px] text-muted/70">
          auto every {Math.round((status.interval_minutes ?? 360) / 60)}h
        </span>
      ) : null}

      {error ? <span className="text-[12px] text-warn">{error}</span> : null}
    </div>
  );
}
