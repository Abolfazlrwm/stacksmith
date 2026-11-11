# ADR-0014: OpenTelemetry traces to Tempo

- **Status:** accepted
- **Date:** 2026-11-19
- **Supersedes:** —

## Context

v0.2.0 ships metrics (Prometheus) and logs (Loki). The missing signal is
traces: when a request is slow, the operator can see *that* it was slow
(the metric) and *what* logged (the log), but not *where* the time went
inside the request — the middleware, the query, the redis call, the
celery task.

The v0.3 roadmap (issue #20) lists "Distributed tracing" as the fourth
item.

## Decision

Instrument the Django app with OpenTelemetry auto-instrumentation:
Django (HTTP spans), psycopg (database spans), redis (cache spans), and
celery (task spans). Traces export over OTLP/HTTP to Tempo, a
single-node trace store in the monitoring overlay. Grafana gains a Tempo
datasource with traces-to-logs and traces-to-metrics links.

## Rationale

- **Auto-instrumentation, not manual spans.** The OpenTelemetry
  instrumentor packages wrap Django, psycopg, redis and celery
  automatically. No manual `tracer.start_span()` calls in application
  code. Every request gets a full span tree for free.
- **Tempo over Jaeger.** Tempo is Grafana-native (same datasource
  pattern as Loki), stores traces on the local filesystem, and has no
  external dependencies. Jaeger requires Elasticsearch or Cassandra for
  storage.
- **OTLP/HTTP, not gRPC.** HTTP avoids the gRPC port and certificate
  complexity. Tempo listens on :4318 (OTLP/HTTP) and :14268 (Jaeger
  thrift). The app posts to `http://tempo:4318/v1/traces`.
- **Disabled by default.** If `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` is
  empty, `setup_telemetry()` returns immediately — no exporter, no
  overhead. The operator opts in by setting the env var.
- **7-day retention.** Traces are for incident forensics, not long-term
  storage. 7 days is enough to investigate a Friday incident on Monday.
  Configurable in `monitoring/tempo.yml`.

## Considered alternatives

### Jaeger with Elasticsearch

Rejected. Elasticsearch is a JVM, eats RAM, and is overkill for trace
storage on a single VPS. Tempo's filesystem backend is simpler and
sufficient.

### Datadog / APM SaaS

Rejected (ADR-0004, ADR-0009): no cloud lock-in, no off-host data.

### Manual span instrumentation

Rejected for the first pass. Auto-instrumentation covers 95% of the
spans (HTTP, DB, cache, task) with zero code changes. Manual spans can be
added later for business-specific operations.

### Honeycomb / Lightstep

Rejected. Same reasoning as Datadog — SaaS dependency, off-host data.

## Consequences

- `app/requirements.txt` gains `opentelemetry-distro` and
  `opentelemetry-exporter-otlp`.
- `app/config/telemetry.py` configures the tracer provider and
  auto-instruments Django, psycopg, redis, celery.
- `app/entrypoint.sh` calls `setup_telemetry()` before starting gunicorn.
- `docker-compose.monitoring.yml` gains a `tempo` service on ports
  14268 (Jaeger) and 4318 (OTLP/HTTP).
- `monitoring/tempo.yml` configures single-node Tempo with 7-day
  retention and filesystem storage.
- Grafana provisioning gains a Tempo datasource with traces-to-logs and
  traces-to-metrics links.
- `.env.example` gains `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` (empty by
  default).
- The `tracing-drill` workflow enables tracing, hits the app, and
  queries Tempo to verify traces were ingested.
- This decision closes the "Distributed tracing" item from the v0.3
  roadmap (issue #20).
