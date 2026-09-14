"""Minimal in-memory rate limiting.

Single-process only — matches the current single-uvicorn-worker deployment
(see Dockerfile: no --workers flag). If this ever moves to multiple workers
or replicas, this needs a shared store (Redis, etc.) instead.

Not meant to resist a well-resourced, many-IP attacker — this is a small
self-hosted service, and the goal is just to make a single-IP brute force of
a 6-digit pairing code (1e6 space, 15-minute window) take impractically
long, per crypto.py's new_pairing_code() docstring.
"""

from __future__ import annotations

import time
from collections import defaultdict

_attempts: dict[str, list[float]] = defaultdict(list)


def allow(key: str, *, max_attempts: int, window_s: float) -> bool:
    """Record an attempt under `key`; return whether it's within the allowance.

    Prunes attempts outside the window as a side effect, so the dict doesn't
    grow unboundedly over the life of the process.
    """
    now = time.monotonic()
    recent = [t for t in _attempts[key] if now - t < window_s]
    recent.append(now)
    _attempts[key] = recent
    return len(recent) <= max_attempts
