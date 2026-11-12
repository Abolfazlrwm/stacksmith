# ADR-0008: Canary checks post-switch with auto-rollback

- **Status:** accepted
- **Date:** 2026-11-12
- **Supersedes:** the "No canary checks post-switch" item in `docs/known-limitations.md`

## Context

v0.1.0's `deploy.sh` switches 100% of traffic to the new color immediately
after the new instance's healthcheck passes. If the new image is broken in
a way the healthcheck does not catch (slow startup under real load, a bad
migration, a missing env var that only matters on a real request), every
user sees the failure until the operator notices and runs `rollback.sh`.

The v0.2 roadmap (issue #12) lists "canary checks post-switch" as a
desired improvement.

## Decision

After switching the upstream, `deploy.sh` runs `CANARY_PROBES` (default 5)
health probes at `CANARY_INTERVAL` (default 2s) intervals against
`/health/live/` and `/health/ready/` through nginx. If any probe fails,
the upstream is switched back to the old color, nginx is reloaded, and
the deploy exits non-zero. The new color is left running (but serving no
traffic) so the operator can inspect its logs.

## Rationale

- **Catches what the healthcheck misses.** The initial `--wait` healthcheck
  proves the new container is up; the canary proves it is actually serving
  through nginx after the switch. A container that passes its own
  healthcheck but fails when nginx routes to it (bad upstream name, port
  mismatch, broken middleware) is caught here.
- **Fast feedback.** Five probes at two-second intervals means the deploy
  aborts within 10 seconds of a broken switch, not minutes.
- **Auto-rollback, not auto-stop.** The upstream is switched back
  immediately; the old color is already running (we have not stopped it
  yet). There is no need to start anything — just reload nginx.
- **Leaves the bad color running.** Stopping the bad color would discard
  its logs. Leaving it running (with no traffic) means the operator can
  `docker compose logs app-green` to see why the canary failed.
- **Tunable.** `CANARY_PROBES` and `CANARY_INTERVAL` are env vars. CI uses
  3 probes at 1s (fast); production can use 10 probes at 5s (thorough).

## Considered alternatives

### Weighted canary (10% then 50% then 100%)

Rejected for compose. nginx can split traffic between upstreams with
`weight=N`, but compose's blue-green model is binary (one upstream serves
all traffic). A weighted canary would require a second upstream in
`nginx/upstreams.conf` and a weighted split — more moving parts, more
failure modes, and the health probe failure rate at 10% traffic is the
same as at 100% (a probe either works or it does not). The binary
canary (all traffic, but probe before draining the old color) catches
the same failures with simpler machinery.

### External canary tool (Flagger, Argo Rollouts)

Rejected. These are Kubernetes-native. We are on compose (ADR-0001). The
canary logic is 15 lines of bash; a CRD-based tool is not justified.

### No canary (rely on the healthcheck)

Rejected. This is the v0.1.0 behavior. The healthcheck proves the
container is up, not that nginx can reach it after the upstream switch.
The gap is real and the canary closes it.

## Consequences

- `deploy.sh` runs canary probes after the upstream switch. A failed
  probe rolls the upstream back to the old color and exits non-zero.
- The old color is not stopped until the canary passes. This extends the
  overlap window by `CANARY_PROBES * CANARY_INTERVAL` seconds (default
  10s). Both colors run during this window.
- The bad color is left running after a failed canary. The operator must
  stop it manually (`docker compose stop app-green`) after inspecting
  logs. This is intentional — auto-stopping would discard logs.
- The `deploy + rollback drill` CI job now runs with canary probes. A new
  `canary failure → auto-rollback` CI job proves the rollback path by
  breaking app-green (killing gunicorn inside the container) after it
  passes its initial healthcheck, then confirming deploy.sh rolls back.
- This decision closes the "canary checks post-switch" item from the v0.2
  roadmap (issue #12).
