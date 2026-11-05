# ADR-0002: Blue-green deploys with compose, not rolling updates

- **Status:** accepted
- **Date:** 2026-11-05
- **Supersedes:** —

## Context

Phase 1 ships a single `app` container behind nginx. When a new image is
built, the old container must be replaced. The question is how: a rolling
update, a recreate, or a blue-green switch.

The constraint is zero downtime. The docubot API serves live traffic; even
a few seconds of 502s during a deploy is visible to users and to the
uptime probe (Phase 4).

## Decision

Use blue-green deploys at the compose service level. The compose file
defines two app instances — `app-blue` and `app-green` — and nginx routes
to one at a time via `nginx/upstreams.conf`. `scripts/deploy.sh` starts
the inactive instance, waits for its healthcheck, switches the upstream,
reloads nginx, and stops the old instance after a grace period.

## Rationale

- **Zero downtime.** The new instance is up and healthy before the upstream
  switches. nginx reload is graceful — old workers finish in-flight
  requests, new workers use the new upstream. There is no window where no
  instance is serving.
- **Instant rollback.** The previous instance is stopped, not removed.
  `scripts/rollback.sh` starts it again and switches back. There is no
  image rebuild on the rollback path.
- **Fits compose.** Compose has no built-in rolling update. `docker compose
  up -d --force-recreate app` stops the old container before starting the
  new one — there is a downtime window. Blue-green with two named services
  is the compose-native way to get zero downtime.
- **Single host.** Both instances run on the same VPS. The host needs
  enough RAM for two app processes during the switch window (typically
  under a minute). For docubot's footprint this is fine.

## Considered alternatives

### Rolling update (`docker compose up -d --force-recreate`)

Rejected. Compose's recreate stops the old container before starting the
new one. The gap is small (seconds) but real, and it shows up as 502s on
the uptime probe. There is no `maxSurge` / `maxUnavailable` knob in
compose; that is a Kubernetes concept.

### Kubernetes `Deployment` with `RollingUpdate` strategy

Rejected with Kubernetes (see ADR-0001). Even if we were on Kubernetes,
a rolling update alone does not give zero downtime for a single-replica
deployment — you need at least two replicas and a readiness gate, which is
blue-green in everything but name.

### Recreate with nginx `proxy_next_upstream`

Rejected. Configuring nginx to fall back to a backup upstream when the
primary fails adds complexity and masks deploy failures — a broken new
instance would silently fall back to the old one, and you would not know
until the old one is also gone. Blue-green with an explicit switch makes
the deploy decision visible.

### Heroku-style slug deployment

Rejected. We are not on Heroku and do not want a platform dependency. The
deploy primitive should be `docker compose`, not a platform-specific CLI.

## Consequences

- The compose file has two app services (`app-blue`, `app-green`) instead
  of one. They share the same image, env and healthcheck; only the name
  differs.
- `nginx/upstreams.conf` is rewritten by `deploy.sh` and should not be
  edited by hand.
- During a deploy, both instances run briefly. The host must have enough
  memory for two app processes. If it does not, reduce `GUNICORN_WORKERS`
  or move to a larger VPS.
- Database migrations run on both instances (the entrypoint runs
  `migrate --noinput`). Django's migration lock serializes them; the
  second instance's migrate is a no-op once the first has applied them.
- There is no canary step. A bad deploy goes live to 100% of traffic
  immediately. Canary checks post-switch are on the v0.2 roadmap.
