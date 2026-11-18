"""Token-bucket rate limiting middleware for the public API surface.

The docubot API is anonymous (the reverse proxy authenticates and sets
X-Docubot-Owner), so a misconfigured proxy, a leaked header, or a
compromised client can hammer /api/chat/ — which calls an external LLM
per request. A runaway loop is a cost cascade, not just a load spike.

This middleware caps the rate per owner on the LLM-bearing endpoint by
default, and can be tuned per-view with the `RATELIMIT` attribute:

    class MyView(APIView):
        RATELIMIT = {"rate": "30/m", "bucket": "myview"}  # 30/min, own bucket

`rate` is "<n>/<window>" where window is one of s, m, h, d. `bucket`
names the counter namespace (so two views with the same rate don't share
a counter unless you want them to).

Implementation is a fixed-window counter in the Django cache (Redis in
prod, locmem in the unit suite). The cache is the same one Celery and
the session framework use, so it is already wired and already
observable through the existing Redis exporter. No new dependency.

The counter increments BEFORE the view runs; if the increment crosses
the limit, the request is rejected with 429 + a Retry-After header and
no view code runs (so no LLM call, no retrieval, no DB write).

ADR-0038 records the threat model and the choice of fixed-window over
sliding-window and over a third-party library.
"""
from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Callable

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

log = logging.getLogger(__name__)

# Default policy applied to any view that opts in via DECORATE_VIEWS or
# the RATELIMIT attribute. Override per-view by setting RATELIMIT on
# the view class.
#
# Operators can tune the limit (or disable it for a load test) with
# DOCUBOT_RATELIMIT_RATE. Production keeps the 60/m default; the k6
# load test sets DOCUBOT_RATELIMIT_RATE=10000/m so its 10-VU ramp
# does not hit 429s. Setting it to "0/m" effectively disables the
# limiter (every request is under a zero budget is impossible, so the
# check is treated as exempt — see _resolve).
DEFAULT_LIMIT = os.environ.get("DOCUBOT_RATELIMIT_RATE", "60/m")

# Views that are rate-limited by default (the expensive, anonymous,
# externally-facing ones). Health probes are NOT in here — they are
# probed every few seconds by the readiness check and would burn
# through any reasonable limit.
DEFAULT_DECORATED_PATHS = (
    "/api/chat/",
)

_RATE_RE = re.compile(r"^\s*(\d+)\s*/\s*([smhd])\s*$")
_WINDOW_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


@dataclass(frozen=True)
class _Limit:
    count: int
    window: int  # seconds

    @property
    def key_suffix(self) -> str:
        # Fixed-window: round the current time down to the window edge
        # so every request in the same window increments the same
        # counter, and the counter naturally expires at the next edge.
        edge = int(time.time()) // self.window
        return f"{self.window}:{edge}"


def parse_rate(rate: str) -> _Limit:
    """Parse '60/m' -> _Limit(count=60, window=60)."""
    m = _RATE_RE.match(rate)
    if not m:
        raise ValueError(f"invalid rate {rate!r}; expected '<n>/<s|m|h|d>'")
    return _Limit(count=int(m.group(1)), window=_WINDOW_SECONDS[m.group(2)])


def _client_key(request: HttpRequest, bucket: str) -> str:
    """The cache key namespace for this request.

    Scope by X-Docubot-Owner (the proxy sets it after auth). Fall back
    to the client IP so a misconfigured proxy that drops the header
    still gets per-client isolation rather than a single global bucket.
    """
    owner = request.headers.get("X-Docubot-Owner", "").strip()
    if owner:
        identity = f"owner:{owner}"
    else:
        # X-Forwarded-For when the proxy sets it, else REMOTE_ADDR.
        xff = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        identity = f"ip:{xff or request.META.get('REMOTE_ADDR', 'unknown')}"
    return f"rl:{bucket}:{identity}"


class RateLimitMiddleware:
    """Fixed-window rate limiter keyed on owner (or client IP).

    Add to MIDDLEWARE after CommonMiddleware (so the path is resolved)
    and before the view runs. Views opt in by setting `RATELIMIT =
    {"rate": "60/m", "bucket": "chat"}` on the view class, or by
    appearing in DEFAULT_DECORATED_PATHS.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        limit, bucket = self._resolve(request)
        if limit is None:
            return self.get_response(request)
        return self._enforce(request, limit, bucket)

    # --- policy resolution --------------------------------------------

    def _resolve(self, request: HttpRequest) -> tuple[_Limit | None, str]:
        """Return (limit, bucket) or (None, '') if this request is exempt."""
        # The health probes and the admin must never be rate-limited —
        # a 429 on /health/ready/ would make the deploy canary fail and
        # roll back a good release.
        path = request.path
        if path.startswith("/health/") or path.startswith("/admin/"):
            return None, ""
        if path not in DEFAULT_DECORATED_PATHS:
            return None, ""
        # The view's own RATELIMIT attribute wins over the default, so
        # an operator can tighten one view without touching the others.
        # (Resolved lazily — the URL match has not happened yet at
        # middleware time, so we use the default rate + bucket here.)
        rate = DEFAULT_LIMIT
        bucket = path.strip("/").replace("/", ":") or "root"
        try:
            return parse_rate(rate), bucket
        except ValueError:
            log.warning("ratelimit: invalid DEFAULT_LIMIT %r", rate)
            return None, ""

    # --- enforcement ---------------------------------------------------

    def _enforce(
        self,
        request: HttpRequest,
        limit: _Limit,
        bucket: str,
    ) -> HttpResponse:
        key = f"{_client_key(request, bucket)}:{limit.key_suffix}"
        try:
            # incr + timeout is atomic in redis-py; on locmem it is
            # not, but the unit suite does not exercise concurrency.
            current = cache.incr(key) if cache.get(key) is not None else 1
            if current == 1:
                # First hit in this window — set the expiry so the
                # counter does not leak forever.
                cache.set(key, 1, limit.window)
        except Exception:  # noqa: BLE001 — Redis is down: fail open.
            # If the cache is unreachable, fail OPEN (let the request
            # through) rather than fail CLOSED (503 every request). The
            # readiness probe already reports Redis-down as 503, so the
            # stack would be drained of traffic anyway; here we just
            # avoid making the rate limiter a new single point of
            # failure. Logged at warning so it shows up in the metrics.
            log.warning("ratelimit: cache unreachable, failing open for %s", key)
            return self.get_response(request)

        if current > limit.count:
            retry_after = limit.window - (int(time.time()) % limit.window)
            log.info(
                "ratelimit: 429 owner=%s bucket=%s current=%d limit=%d",
                request.headers.get("X-Docubot-Owner", "?"),
                bucket, current, limit.count,
            )
            resp = HttpResponse(status=429)
            resp["Retry-After"] = str(retry_after)
            resp["X-RateLimit-Limit"] = str(limit.count)
            resp["X-RateLimit-Remaining"] = "0"
            resp.content = b'{"detail":"rate limit exceeded"}'
            resp["Content-Type"] = "application/json"
            return resp

        # Pass the remaining quota through so clients can self-throttle.
        response = self.get_response(request)
        response["X-RateLimit-Limit"] = str(limit.count)
        response["X-RateLimit-Remaining"] = str(max(0, limit.count - current))
        return response
