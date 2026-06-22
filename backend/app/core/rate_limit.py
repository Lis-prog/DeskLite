"""In-memory sliding-window rate limiter for authentication endpoints.

Single-process deployments (uvicorn workers=1, local dev) share one bucket store.
Sufficient for DeskLite's capstone scale; swap for Redis if we add horizontal scale.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import settings

_lock = Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    """Best-effort client IP; honours the first X-Forwarded-For hop behind a proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def _check(key: str, *, max_calls: int, window_seconds: int) -> int | None:
    """Record a hit. Returns Retry-After seconds when limited, else None."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = [t for t in _hits[key] if t > cutoff]
        if len(bucket) >= max_calls:
            retry_after = int(window_seconds - (now - bucket[0])) + 1
            return max(retry_after, 1)
        bucket.append(now)
        _hits[key] = bucket
    return None


def clear_rate_limits() -> None:
    """Reset all buckets — used in tests."""
    with _lock:
        _hits.clear()


def enforce_auth_rate_limit(request: Request) -> None:
    """FastAPI dependency: throttle public auth POST routes per client IP."""
    if not settings.auth_rate_limit_enabled:
        return

    key = f"auth:{client_ip(request)}"
    retry_after = _check(
        key,
        max_calls=settings.auth_rate_limit_max,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
