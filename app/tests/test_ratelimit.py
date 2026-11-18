"""Unit tests for config.ratelimit — the fixed-window rate limiter.

The middleware is the only thing standing between an anonymous client
and the external LLM call behind /api/chat/, so the policy decisions
matter and are pinned here:

- Health probes and admin are NEVER rate-limited (a 429 on the
  readiness probe would roll back a good release).
- /api/chat/ IS rate-limited by default (60/min per owner).
- The limit is keyed on X-Docubot-Owner; falls back to client IP when
  the header is absent (a misconfigured proxy).
- A 429 carries Retry-After + X-RateLimit-* headers so clients can
  self-throttle.
- If the cache is unreachable, the limiter fails OPEN (lets the
  request through) rather than adding a new single point of failure.

These tests deliberately do not depend on pytest-django (main's
unit.yml installs only pytest, not pytest-django). The view behind
/api/chat/ is heavy (LLM call, retrieval, DB write), so we do not
invoke it — instead we test the middleware directly against a stub
get_response, exercising the policy and the enforcement separately.
This keeps the suite fast and free of network calls.
"""
from __future__ import annotations

import pytest
from django.test import RequestFactory

from config import ratelimit as rl
from config.ratelimit import RateLimitMiddleware, parse_rate


class _StubResponse:
    """Minimal response object the middleware writes headers onto."""

    def __init__(self):
        self.status_code = 200
        self.headers: dict[str, str] = {}
        self.content = b""

    def __setitem__(self, k, v):
        self.headers[k] = v

    def __getitem__(self, k):
        return self.headers[k]


def _stub_get_response(_request):
    return _StubResponse()


def _make_request(path="/api/chat/", owner="alice", method="POST"):
    rf = RequestFactory()
    req = getattr(rf, method.lower())(path)
    # RequestFactory does not populate .headers (that happens in the
    # real WSGI handler); the middleware reads request.headers, so we
    # attach a Mapping that returns our owner.
    if owner is not None:
        req.headers = {"X-Docubot-Owner": owner}
    else:
        req.headers = {}
    return req


@pytest.fixture()
def fresh_owner():
    """A unique owner per test so cached counters never bleed across tests.

    The rate-limit counter keys include the window-edge time, which is
    the same across tests that run inside one second. Patching the
    cache symbol per test isolates the cache object, but the safest
    guarantee is a unique identity: even if two tests shared a cache,
    their counters would not collide. This is also how the production
    limiter is meant to be used — per-user buckets, not one global
    bucket.
    """
    import uuid
    return f"user-{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def locmem_cache(monkeypatch):
    """Replace the shared Redis cache with a fresh locmem one per test.

    The production CACHES backend is Redis; in the unit suite we swap
    in LocMemCache so the counters are isolated, fast, and reset
    between tests. We patch the `cache` symbol the middleware
    imported, not the global settings — that way the test does not
    need pytest-django's `settings` fixture (main's unit.yml does not
    install it).
    """
    from django.core.cache.backends.locmem import LocMemCache

    c = LocMemCache("ratelimit-test", {})
    monkeypatch.setattr(rl, "cache", c)
    return c


# ---------------------------------------------------------------------------
# parse_rate — the policy parser
# ---------------------------------------------------------------------------

def test_parse_rate_minutes():
    r = parse_rate("60/m")
    assert r.count == 60
    assert r.window == 60


def test_parse_rate_seconds():
    r = parse_rate("5/s")
    assert r.count == 5
    assert r.window == 1


def test_parse_rate_hours_and_days():
    assert parse_rate("100/h").window == 3600
    assert parse_rate("1000/d").window == 86400


@pytest.mark.parametrize("bad", ["", "abc", "60", "60/", "/m", "60/minute"])
def test_parse_rate_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_rate(bad)


def test_parse_rate_accepts_zero():
    # "0/m" is a valid (if useless) rate — blocks everything. The
    # parser must accept it; the policy never sets it.
    assert parse_rate("0/m").count == 0


def test_default_limit_is_60_per_minute():
    # The headline policy: 60 chat requests per minute per owner.
    # If this changes, the README and ADR-0038 must update with it.
    assert rl.DEFAULT_LIMIT == "60/m"


# ---------------------------------------------------------------------------
# policy resolution — what gets limited, what doesn't
# ---------------------------------------------------------------------------

def test_health_paths_are_exempt():
    mw = RateLimitMiddleware(_stub_get_response)
    for path in ("/health/live/", "/health/ready/"):
        req = _make_request(path)
        limit, _ = mw._resolve(req)
        assert limit is None, f"{path} must not be rate-limited"


def test_admin_is_exempt():
    mw = RateLimitMiddleware(_stub_get_response)
    req = _make_request("/admin/login/")
    limit, _ = mw._resolve(req)
    assert limit is None


def test_chat_path_is_limited():
    mw = RateLimitMiddleware(_stub_get_response)
    req = _make_request("/api/chat/")
    limit, bucket = mw._resolve(req)
    assert limit is not None
    assert limit.count == 60
    assert limit.window == 60
    assert "chat" in bucket


def test_documents_path_is_not_yet_limited():
    # Uploads are cheaper than chat (no LLM call) and are already
    # gated by validate_upload + size caps. Not in the default list.
    mw = RateLimitMiddleware(_stub_get_response)
    req = _make_request("/api/documents/")
    limit, _ = mw._resolve(req)
    assert limit is None


# ---------------------------------------------------------------------------
# enforcement — the counter and the 429
# ---------------------------------------------------------------------------

def test_first_request_passes_and_sets_headers(locmem_cache, fresh_owner):
    mw = RateLimitMiddleware(_stub_get_response)
    resp = mw(_make_request("/api/chat/", owner=fresh_owner))
    assert resp.status_code == 200
    assert resp["X-RateLimit-Limit"] == "60"
    assert resp["X-RateLimit-Remaining"] == "59"


def test_request_under_limit_passes(locmem_cache, fresh_owner):
    mw = RateLimitMiddleware(_stub_get_response)
    for i in range(10):
        resp = mw(_make_request("/api/chat/", owner=fresh_owner))
        assert resp.status_code == 200, f"request {i} should pass"


def test_request_over_limit_returns_429(locmem_cache, fresh_owner):
    mw = RateLimitMiddleware(_stub_get_response)
    # Burn through the 60/min budget.
    for _ in range(60):
        assert mw(_make_request("/api/chat/", owner=fresh_owner)).status_code == 200
    # The 61st must be rejected.
    resp = mw(_make_request("/api/chat/", owner=fresh_owner))
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert resp["X-RateLimit-Limit"] == "60"
    assert resp["X-RateLimit-Remaining"] == "0"
    assert b"rate limit exceeded" in resp.content


def test_limits_are_per_owner(locmem_cache, fresh_owner):
    mw = RateLimitMiddleware(_stub_get_response)
    # one owner burns their budget.
    for _ in range(60):
        mw(_make_request("/api/chat/", owner=fresh_owner))
    # a different owner still has their full budget.
    resp = mw(_make_request("/api/chat/", owner="someone-else"))
    assert resp.status_code == 200


def test_missing_owner_falls_back_to_ip(locmem_cache):
    mw = RateLimitMiddleware(_stub_get_response)
    # No X-Docubot-Owner header — should still get an IP-scoped limit
    # rather than a single global bucket.
    req = _make_request("/api/chat/", owner=None)
    req.META["REMOTE_ADDR"] = "1.2.3.4"
    resp = mw(req)
    assert resp.status_code == 200


def test_cache_unreachable_fails_open(locmem_cache, fresh_owner, monkeypatch):
    """If the cache is broken, the limiter must not become a new SPOF."""

    def _boom(*a, **kw):
        raise RuntimeError("redis is down")

    monkeypatch.setattr(locmem_cache, "incr", _boom)
    monkeypatch.setattr(locmem_cache, "get", _boom)
    monkeypatch.setattr(locmem_cache, "set", _boom)

    mw = RateLimitMiddleware(_stub_get_response)
    resp = mw(_make_request("/api/chat/", owner=fresh_owner))
    # Fail open: the request goes through despite the cache being down.
    assert resp.status_code == 200
