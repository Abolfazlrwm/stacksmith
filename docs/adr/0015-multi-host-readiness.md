# ADR-0015: Multi-host readiness — what it would take to leave one VPS

- **Status:** deferred (evaluation, not a decision to act)
- **Date:** 2026-11-20
- **Supersedes:** nothing; this reopens ADR-0001 if read-only-host scaling is needed

## Context

ADR-0001 chose compose on a single VPS. Every subsequent ADR has been
consistent with that: blue-green with two compose services on one host
(ADR-0002), dump-based backups (ADR-0003), Alertmanager on one host
(ADR-0011), Tempo on one host (ADR-0014).

The v0.3 roadmap (issue #20) lists "Multi-host readiness" as an
evaluation item — not a commitment to move, but a written answer to
"what would it take if we had to?".

## Decision

Do not move to multi-host now. Document what it would take, so the
decision can be reopened quickly when a real requirement arrives
(traffic that one VPS cannot handle, a HA requirement, a geographic
distribution requirement).

## What changes if we move to two hosts

### Postgres

The biggest change. Today postgres runs in a container on the VPS, with
a named volume. Two options for multi-host:

1. **Managed Postgres** (RDS, CloudSQL, Neon). Removes the database
   from the VPS entirely. The app connects over the network. Backups
   become the provider's job (ADR-0003 is reopened — we stop running
   pg_dump and rely on PITR). This is the simplest path; it is also the
   one that most violates "no cloud lock-in" (ADR-0001).

2. **Postgres with streaming replication**. A primary on host A, a
   replica on host B, a virtual IP or DNS round-robin in front. This is
   real HA but requires managing replication slots, failover (patroni or
   repmgr), and WAL archiving (ADR-0003 is reopened). It is the
   self-hosted equivalent of managed Postgres.

Either way, the `postgres` service leaves `docker-compose.prod.yml`.

### Redis

Redis is used as both the Celery broker and the Django cache. For
multi-host:

1. **Managed Redis** (ElastiCache, Upstash). Simplest.
2. **Redis Sentinel**. Three sentinel processes across two hosts,
   monitoring a primary and a replica. Failover is automatic but
   requires sentinel-aware clients (django-redis supports it).

The `redis` service leaves `docker-compose.prod.yml`.

### nginx + blue-green

Today nginx and the app are on the same host. For multi-host:

1. **Load balancer** in front of two hosts, each running the app. The
   blue-green deploy becomes a rolling deploy across the two hosts.
2. **Session stickiness** if the app uses server-side sessions (docubot
   uses JWT, so no stickiness needed). If sessions move to Redis (they
   already are, via the cache backend), stickiness is not required.

### Backups

`backup-db.sh` runs on the VPS and connects to postgres via the docker
network. If postgres moves off the VPS, `backup-db.sh` connects over the
network. The restore drill (ADR-0003) still works; the encryption
(ADR-0007) still works; the integrity verification (ADR-0012) still
works. The only change is the connection string.

### Observability

Prometheus, Grafana, Loki, Tempo, Alertmanager all run on the VPS. For
multi-host, they would either:

- Stay on one host and scrape the other host's exporters (via
  federation or remote_write).
- Move to a dedicated observability host.

Neither is hard; it is a networking and config change.

## What does NOT change

- The app code does not change. Django, Celery, the health endpoints —
  all the same.
- The deploy script's logic does not change. `deploy.sh` still does
  blue-green; the difference is that the blue and green instances are on
  different hosts.
- The ADRs do not change (except ADR-0001, which is reopened).
- The CI drills do not change (they test against a single-host compose
  stack; the multi-host deployment is tested separately).

## Cost estimate

| Component | Single VPS (today) | Two hosts |
|---|---|---|
| Compute | 1 × 4 vCPU / 8 GB | 2 × 4 vCPU / 8 GB |
| Postgres | included | +managed (≈$50/mo) or +replica host |
| Redis | included | +managed (≈$20/mo) or +sentinel |
| Network | included | +cross-host traffic |

Roughly: moving to two hosts doubles the compute cost and adds
managed-service cost. For a knowledge-base backend without SLA
requirements, this is not justified today.

## When to reopen this

- Traffic exceeds what one 4 vCPU VPS can handle (measured: CPU
  consistently > 80% at peak).
- An SLA requires < 5 min RTO (single-host restart is ~2 min; multi-host
  failover is ~30s).
- Geographic distribution is required (deploy in two regions for
  latency).

Until one of these is true, ADR-0001 stands: single host, compose.
