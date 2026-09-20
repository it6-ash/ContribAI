"""Per-identity rate limiting and a spend ceiling for model calls.

The failure this exists to prevent is not a traffic spike, it is a bill. Every
Groq call was previously unbounded per user: one signed-in account could sit in
a loop on the workspace chat and spend the project's budget. Request counts
alone do not bound cost either, so there is a token ceiling alongside the rate.

ponytail: an in-process token bucket, not Redis. This app is single-process by
design (the scheduler's docstring says the same), and a dict with a lock is the
whole implementation. The moment there is a second worker this under-counts by
the number of workers, which is the point at which it should move to Redis.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

log = logging.getLogger("contribai.limits")


@dataclass
class _Bucket:
    tokens: float
    updated: float
    spent_units: float = 0.0
    window_start: float = field(default_factory=time.monotonic)


class RateLimiter:
    """Token bucket per key, plus a coarse per-window usage ceiling."""

    def __init__(
        self,
        *,
        rate_per_minute: float,
        burst: int,
        units_per_window: float | None = None,
        window_seconds: float = 3600.0,
    ):
        self.rate = rate_per_minute / 60.0
        self.burst = burst
        self.units_per_window = units_per_window
        self.window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def check(self, key: str, units: float = 0.0) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self.burst, updated=now)
                self._buckets[key] = bucket
                self._evict(now)

            elapsed = now - bucket.updated
            bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rate)
            bucket.updated = now

            if now - bucket.window_start > self.window_seconds:
                bucket.window_start = now
                bucket.spent_units = 0.0

            if self.units_per_window is not None and bucket.spent_units >= self.units_per_window:
                retry = int(self.window_seconds - (now - bucket.window_start)) + 1
                return False, max(retry, 1)

            if bucket.tokens < 1:
                return False, max(int((1 - bucket.tokens) / self.rate) + 1, 1)

            bucket.tokens -= 1
            bucket.spent_units += units
            return True, 0

    def _evict(self, now: float) -> None:
        """Keep the dict bounded; an unbounded key space is its own DoS."""
        if len(self._buckets) <= 5000:
            return
        stale = [k for k, b in self._buckets.items() if now - b.updated > self.window_seconds]
        for k in stale:
            self._buckets.pop(k, None)
        if len(self._buckets) > 5000:  # still full: drop the oldest half
            for k in sorted(self._buckets, key=lambda k: self._buckets[k].updated)[:2500]:
                self._buckets.pop(k, None)


# Model-backed endpoints. Generous for a human, ruinous for a loop.
llm_limiter = RateLimiter(
    rate_per_minute=10, burst=15, units_per_window=120_000, window_seconds=3600
)

# Everything else authenticated, to bound scraping and accidental client loops.
api_limiter = RateLimiter(rate_per_minute=240, burst=120)
