# ADR-0004: Metrics-first, logs-second observability

- **Status:** accepted
- **Date:** 2026-11-07
- **Supersedes:** —

## Context

The stack needs observability: when something breaks, the operator must be
able to find it fast. The two main signals are metrics (numbers over time)
and logs (events with context). The question is which one is the primary
lens and which is the secondary.

## Decision

Make metrics the primary lens and logs the secondary. Ship a Prometheus
instance that scrapes node-exporter, cAdvisor, the app and a blackbox
probe; ship alert rules for the failures that actually happen (backup
staleness, disk saturation, restart storms, health probe failures, 5xx
rate); and ship two provisioned Grafana dashboards. Logs stay in the
json-file driver on each container (Phase 1) and are read with
`docker compose logs` during an incident.

## Rationale

- **Metrics are cheap to scan; logs are expensive.** A dashboard with six
  panels tells you in two seconds whether the system is healthy. Grepping
  logs for the same answer takes minutes. In an incident, the dashboard is
  the first thing you open; the logs are the second.
- **Alerts need metrics.** "Page me when the disk is 85% full" is a metric
  alert. "Page me when a specific log line appears" is possible but
  brittle and noisy. The alert rules in `monitoring/alert_rules.yml` are
  all metric-based.
- **Backup freshness is a metric, not a log.** The most important
  operational question after "is the app up" is "is the backup fresh".
  That is a single number (hours since the last successful backup),
  scraped from a textfile exporter, alerted on at 26 hours, and pinned to
  the business dashboard. It cannot be a log line.
- **Logs are already structured.** Phase 1 ships json-file logging on
  every service, and the Django settings emit JSON-formatted log lines.
  `docker compose logs <service>` is sufficient for incident forensics.
  A log aggregation stack (Loki, Elasticsearch) is not justified for a
  single VPS.

## Considered alternatives

### Logs-first (Loki + Promtail)

Rejected as the primary lens. Loki is excellent and cheap, but logs do
not answer "is the system healthy right now" as fast as a metric dashboard.
We would still need metrics for alerting, so Loki would be additive, not
alternative. It is on the v0.2 roadmap as a secondary signal, not a
replacement for metrics.

### Full APM (OpenTelemetry, Jaeger, Sentry)

Rejected for this scale. Distributed tracing and error tracking are
valuable for a large team with many services. For a single VPS with one
backend, the app's JSON logs and the Django request log are sufficient
for root-causing a specific failure.

### Managed monitoring (Grafana Cloud, Datadog)

Rejected. The deployment target is a single VPS with no cloud lock-in.
A managed monitoring stack would either send data off-host (which the
secrets policy discourages) or cost more than the VPS itself.

## Consequences

- Prometheus, node-exporter, cAdvisor, blackbox-exporter and Grafana run
  as compose services alongside the app stack.
- Alert rules live in `monitoring/alert_rules.yml` and are loaded by
  Prometheus. They are version-controlled and reviewed.
- Grafana dashboards are provisioned from `grafana/dashboards/` — no
  manual dashboard editing in production.
- The backup script must write a textfile metric
  (`monitoring/textfile/backup.prom`) so the backup-freshness alert has
  data to evaluate. (This is a known gap; see the v0.2 roadmap.)
- There is no log aggregation. During an incident, the operator reads
  logs with `docker compose logs`. This is adequate for a single host.
