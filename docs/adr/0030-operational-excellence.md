# ADR-0030: Maintenance window, recording rules, health CLI, capacity, audit

- **Status:** accepted
- **Date:** 2026-12-12
- **Supersedes**: —

## Context

v0.8.0 ships a complete deploy → monitor → backup → restore cycle with
multi-provider Terraform, architecture docs, and an OpenAPI spec. What is
missing is the operational polish that separates a good kit from a great
one:

1. No maintenance mode — the operator cannot serve a 503 during planned
   downtime without stopping the app.
2. No recording rules — dashboards query raw metrics at 15s granularity,
   which is slow for 7-day views.
3. No one-command health check — the operator runs five separate curl
   commands to verify the stack.
4. No capacity planning — the operator cannot predict when disk or memory
   will be exhausted.
5. No audit trail — deploys, rollbacks, restores, and rotations are not
   logged.

## Decision

Add five operational features:

1. **`scripts/maintenance.sh`** — puts nginx into 503 mode for non-health
   routes. Health probes (`/health/live/`, `/health/ready/`) still return
   200 so monitoring does not page. A textfile metric
   (`stacksmith_maintenance_active`) records the state.

2. **`monitoring/recording_rules.yml`** — Prometheus recording rules that
   pre-compute CPU %, memory MB, disk %, nginx p95 latency, error rate,
   backup age, restart count, and maintenance status at 30s intervals.
   Loaded by `prometheus.yml`.

3. **`scripts/stacksmith-health.sh`** — a one-command CLI that checks
   nginx reachability, app liveness, app readiness, backup freshness, and
   maintenance mode. Exits 0 if all pass, 1 if any fails.

4. **`grafana/dashboards/capacity.json`** — a capacity planning dashboard
   with CPU/memory 7-day trends, disk growth rate, predicted disk
   exhaustion (days until 90%), container restart count, and request rate.

5. **`scripts/audit-log.sh`** — an append-only JSON audit log
   (`deploy/state/audit.log`) called by `deploy.sh`, `rollback.sh`,
   `restore-db.sh`, and `backup-db.sh`. Each entry records timestamp,
   action, details, user, and host.

## Rationale

- **Maintenance mode without stopping the app.** A 503 at the nginx layer
  lets the operator do planned maintenance (postgres vacuum, index
  rebuild, cert renewal) without users seeing connection errors. Health
  probes stay 200 so Alertmanager does not page.

- **Recording rules save dashboard latency.** A 7-day CPU chart queries
  `rate(container_cpu_usage_seconds_total[5m])` at every point —
  thousands of samples. A recording rule pre-computes this every 30s, so
  the dashboard queries one value per 30s interval. 10× faster.

- **One-command health check.** An operator at 3am should not type five
  curl commands. `stacksmith-health.sh` runs them all and prints a
  color-coded summary.

- **Capacity planning is forward-looking.** The disk exhaustion prediction
  panel answers "when will we run out of disk?" — the question that
  prevents the 3am disk-full incident.

- **Audit log is the forensic record.** "Who deployed what and when?" is
  unanswerable without a log. The JSON-lines format is greppable and
  parseable by jq.

## Consequences

- `maintenance.sh` writes `nginx/maintenance-on.conf` and
  `monitoring/textfile/maintenance.prom`.
- `recording_rules.yml` is loaded alongside `alert_rules.yml`.
- `stacksmith-health.sh` is a standalone CLI (no dependencies beyond
  curl).
- `capacity.json` is the 7th Grafana dashboard (provisioned).
- `audit-log.sh` is called by 4 scripts; `deploy/state/audit.log` is
  gitignored (runtime state).
- `deploy/state/` is added to `.gitignore`.
