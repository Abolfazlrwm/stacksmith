# ADR-0018: Load testing with k6

- **Status:** accepted
- **Date:** 2026-11-23
- **Supersedes:** —

## Context

Every previous CI drill proves the stack works under a single request:
bring it up, curl `/health`, tear it down. This does not answer "what
happens when 50 users hit the health endpoint at once?" — a question
that matters for two reasons:

1. The health endpoint is probed by the blackbox exporter every 15s, by
   the deploy canary 5 times, and by the uptime probe. Under load, a slow
   health endpoint cascades: the canary fails, the deploy aborts, the
   rollback fires.
2. The app runs gunicorn with 3 workers on a single VPS. If each health
   check takes 50ms, 50 concurrent checks saturate the workers and the
   p95 latency spikes. The load test catches this before production does.

## Decision

Add a `k6` load test workflow that ramps to 50 virtual users over 10
seconds, holds for 30 seconds, and ramps down. The test hits
`/health/live/` through nginx. Two thresholds must hold:

- `p(95) < 500ms` — 95th percentile latency under 500ms.
- `http_req_failed < 1%` — fewer than 1% of requests fail.

If either threshold is breached, the workflow fails.

## Rationale

- **k6 over Locust.** k6 is a single binary, runs in a GitHub Action
  (`grafana/k6-action`), and writes results as metrics. Locust requires
  a Python process per virtual user and a web UI — more moving parts for
  the same answer.
- **k6 over ab/wrk.** ab and wrk are HTTP benchmarks, not load tests.
  They measure raw throughput but not thresholds, checks, or staged
  ramps. k6 has all three.
- **50 VUs, not 500.** The target is a single VPS with 3 gunicorn
  workers. 50 concurrent requests is already 16× oversubscription —
  enough to find a slow query or a lock contention without being
  unrealistic.
- **The health endpoint, not a business endpoint.** The health endpoint
  is the cheapest path through the stack (nginx → gunicorn → JSON
  response, no DB). If even this is slow at 50 VUs, the business
  endpoints are worse. If the health endpoint is fast, the bottleneck
  is elsewhere (DB, redis) and a different test would find it.
- **Thresholds, not just reports.** Without thresholds, a load test is
  a dashboard. With thresholds, it is a gate — a regression that
  doubles p95 latency fails CI.

## Considered alternatives

### Locust

Rejected (see above). Python process per VU, web UI dependency, no
native GitHub Action.

### Vegeta

Rejected. Vegeta is a good hammer but has no staging (constant rate
only) and no check semantics. k6's `stages` and `check` are the right
primitives.

### Gatling

Rejected. Gatling is JVM-based, requires Scala for test authoring, and
is heavier than the problem warrants. k6 is a single Go binary.

### No load testing (rely on the health probe)

Rejected. The blackbox exporter probes once every 15s. That proves the
endpoint is up, not that it is fast under load. The two questions are
different.

## Consequences

- `tests/load/health.js` is the k6 test script. It ramps to 50 VUs,
  holds, ramps down, and checks two thresholds.
- `load-test.yml` workflow brings up the stack, runs k6, and tears down.
  The workflow fails if thresholds are breached.
- The test runs on every push. A performance regression that breaches
  p95 < 500ms or failure rate < 1% blocks the merge.
- The test only covers `/health/live/`. Business-endpoint load tests
  (e.g. a RAG query through the docubot API) require the real docubot
  app, which is not part of this kit. This is a scope decision, not a
  technical limitation.
