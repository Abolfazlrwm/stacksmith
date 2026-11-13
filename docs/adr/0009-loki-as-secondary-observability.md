# ADR-0009: Loki as a secondary observability signal

- **Status:** accepted
- **Date:** 2026-11-13
- **Supersedes:** the "No log aggregation" item in `docs/known-limitations.md`

## Context

v0.1.0 ships metrics-first observability (ADR-0004): Prometheus for
metrics, Grafana for dashboards, json-file logs on each container read
with `docker compose logs`. Logs are the secondary signal — used for
forensics during an incident, not for alerting.

The gap: `docker compose logs <service>` only works on the host, only
shows one service at a time, and has no query language. During an
incident, correlating a 5xx spike (from the metrics dashboard) to the
specific log lines that caused it requires switching context from
Grafana to SSH + `docker compose logs | grep`.

The v0.2 roadmap (issue #12) lists "Loki as a secondary observability
signal" as a desired improvement.

## Decision

Add Loki and promtail to the monitoring overlay. promtail scrapes docker
container logs via the docker socket and ships them to Loki; Loki stores
them for 14 days; Grafana queries Loki through a provisioned datasource.
Metrics stay primary; logs become queryable from the same dashboard.

## Rationale

- **Same dashboard, two signals.** A Grafana panel can mix Prometheus
  (metrics) and Loki (logs) in the same view. The operator sees the 5xx
  spike and the matching log lines without leaving Grafana.
- **Structured labels.** promtail parses the JSON log lines Django emits
  (Phase 1) and extracts `level` and `name` as labels. Queries like
  `{service="app-blue", level="ERROR"}` are immediate.
- **14-day retention.** Enough for post-incident forensics; short enough
  to fit on a single VPS. Configurable in `monitoring/loki.yml`.
- **Single-node mode.** Loki runs in single-node (filesystem) mode, not
  as a distributed cluster. This is the correct deployment for one VPS.
- **Metrics are still primary.** Alerts still come from Prometheus
  (ADR-0004). Loki does not drive alerts; it answers "what did the logs
  say when the metric spiked".

## Considered alternatives

### Elasticsearch / ELK

Rejected. Elasticsearch is a JVM, eats RAM, and is overkill for log
querying on a single host. Loki is purpose-built for this: it indexes
only labels (not full text), stores chunks on the filesystem, and uses
Grafana as its native UI.

### Vector.dev

Rejected. Vector is a excellent log shipper, but it does not include
storage. We would still need Loki (or Elasticsearch) as a backend. Using
promtail → Loki keeps the stack Grafana-native.

### Cloud log aggregation (Grafana Cloud, Datadog Logs)

Rejected. Same reasoning as ADR-0004: no cloud lock-in, no off-host data
shipping. The logs stay on the VPS.

### No log aggregation (keep `docker compose logs`)

Rejected for v0.2. This was the v0.1.0 decision and it was correct then
(metrics-first, ship the minimum). Now that the metrics stack is proven,
adding the secondary signal is the right next step.

## Consequences

- `docker-compose.monitoring.yml` gains `loki` and `promtail` services.
- `monitoring/loki.yml` configures single-node Loki with 14-day retention.
- `monitoring/promtail.yml` configures promtail to scrape docker logs via
  the socket, filter to the `stacksmith` compose project, and parse JSON
  log lines for `level` and `name` labels.
- Grafana provisioning gains a Loki datasource and a "container logs"
  dashboard with service and level template variables.
- promtail mounts the docker socket and `/var/lib/docker/containers` to
  read logs. This is the same access pattern as cAdvisor.
- Logs are still json-file on each container (Phase 1). promtail reads
  them via the docker socket; `docker compose logs` still works for
  SSH-based forensics.
- This decision closes the "Loki as a secondary observability signal"
  item from the v0.2 roadmap (issue #12).
