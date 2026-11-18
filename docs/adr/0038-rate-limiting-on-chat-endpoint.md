# ADR-0038: rate limiting on the LLM-bearing endpoint

- **Status:** accepted
- **Date:** 2026-11-18
- **Supersedes:** none (complements ADR-0037 app hardening)

## Context

v1.2.0 shipped `/api/chat/`, an endpoint that for each request:

1. Embeds the question (local sentence-transformers, ~50 ms CPU).
2. Retrieves the top-k chunks from pgvector (one DB round-trip).
3. Calls an external LLM (OpenAI / Anthropic / Ollama) — the only
   outbound call, and the only one that costs real money per request.
4. Persists the user message, the answer, and the citations (one DB
   write).

The endpoint is anonymous by design: the reverse proxy authenticates
and sets `X-Docubot-Owner`, so the app sees every request as
already-authenticated. That is fine for normal use, but it means a
misconfigured proxy, a leaked header, or a compromised client can
hammer `/api/chat/` with no friction. The result is a cost cascade
(LLM calls are billed per request) plus a load spike on the worker
and the database.

The container drills do not exercise this — they make a handful of
requests, not a flood.

## Decision

Add a fixed-window rate limiter in front of the chat endpoint, keyed
on `X-Docubot-Owner` (falling back to client IP when the header is
absent, so a misconfigured proxy still gets per-client isolation
rather than a single global bucket).

### Policy

- **Default: 60 requests per minute per owner on `/api/chat/`.**
  60/min is one question per second sustained, which is well above
  any human reading pace and well below the rate at which an
  accidental loop or a script becomes a cost problem. The limit is a
  constant in `config/ratelimit.py` so it is easy to find and easy
  to pin in tests.
- **Health probes and admin are exempt.** A 429 on `/health/ready/`
  would make the deploy canary fail and roll back a good release; a
  429 on the admin would lock the operator out. The middleware checks
  the path prefix before resolving the limit.
- **`/api/documents/` is not yet limited.** Uploads are cheaper than
  chat (no LLM call) and are already gated by `validate_upload` +
  the 50 MB size cap. Adding it later is a one-line change to
  `DEFAULT_DECORATED_PATHS`.

### Implementation

Fixed-window counter in the Django cache (Redis in prod, locmem in
the unit suite). The counter key is
`rl:<bucket>:<identity>:<window>:<window-edge>`, where `<window-edge>`
is `floor(now / window)` — so every request in the same window
increments the same counter, and the counter naturally expires at the
next window edge (the cache TTL is set to `window` on the first hit).

Fixed-window is coarser than sliding-window (a client can burst to
2× the limit at a window boundary), but it is:

- **Cheap.** One `INCR` + one `EXPIRE` per request, both O(1) on
  Redis. No sorted sets, no Lua scripts.
- **Simple.** The counter is a single integer; debugging a flood is
  `redis-cli GET rl:chat:owner:alice:60:<edge>`.
- **Good enough.** The threat here is a runaway loop or a careless
  script, not a determined attacker with a botnet. A determined
  attacker would be blocked at the network edge (nginx `limit_req`).
  The app-layer limiter is the second line, not the first.

### Fail-open on cache failure

If the cache is unreachable, the limiter **fails open** (lets the
request through) rather than fail closed (503 every request). The
readiness probe already reports Redis-down as 503, so the stack
would be drained of traffic by the probe before the limiter ever
saw a request; here we just avoid making the limiter a new single
point of failure. The fail-open is logged at warning so it shows up
in the metrics.

### Headers

Every response (200 or 429) carries `X-RateLimit-Limit` and
`X-RateLimit-Remaining` so clients can self-throttle. The 429 also
carries `Retry-After` (seconds until the next window edge).

## Alternatives considered

- **`django-ratelimit` (third-party library).** Rejected: it pulls a
  new dependency, it is decorator-based (which means threading the
  policy through the APIView class hierarchy), and its default
  backend is the cache anyway. The middleware is ~120 lines and has
  no dependency beyond what the app already uses.

- **Sliding-window log.** Rejected: requires a sorted set per client
  (more memory, more Redis ops) for a precision we do not need. The
  fixed-window burst-at-boundary edge case is acceptable here.

- **Token bucket.** Rejected: same precision benefit, same complexity
  cost, and the burst-at-boundary problem is identical to
  fixed-window for the steady-state case.

- **nginx `limit_req` only.** Rejected: nginx is the first line and
  is already the right place for IP-based limiting, but the
  app-layer limiter keys on `X-Docubot-Owner` (which nginx sets
  after auth), so it can enforce per-user quotas that nginx cannot.
  Defense in depth, same logic as ADR-0037's app-layer `SECURE_*`
  headers.

- **Rate-limit `/api/documents/` too.** Deferred: uploads are already
  gated by `validate_upload` and the size cap, and the cost of an
  upload is bounded (CPU for extraction + one DB write). The LLM
  call behind chat is the unbounded cost.

## Consequences

- A client that sends > 60 chat requests per minute gets 429s. The
  normal chat UI sends one request per human turn (~30 s apart), so
  this is invisible to real users.
- The limiter adds one Redis `INCR` + one `EXPIRE` per chat request.
  At the SLO target (P99 < 500 ms), this is noise.
- The limiter is a single file (`config/ratelimit.py`) with a
  constant for the default limit and a tuple for the decorated
  paths, so tuning it is a one-line change.
- If the cache is down, the limiter is a no-op (fail-open). The
  readiness probe catches Redis-down independently.
