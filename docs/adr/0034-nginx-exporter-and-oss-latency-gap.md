# ADR-0034: nginx exporter and the OSS latency gap

- **Status:** accepted
- **Date:** 2026-12-22
- **Supersedes / amends**: amends ADR-0033 (retracts the latency P99 SLO
  and changes the availability SLI source)

## Context

ADR-0033 (v1.1.0) defined an availability SLO and a latency P99 SLO and
wrote alert rules + a Grafana dashboard that queried:

- `nginx_http_requests_total{status=~"5.."}`
- `nginx_http_request_duration_seconds_bucket`

Neither metric exists on a stock OSS nginx + nginx-prometheus-exporter
deployment. The SLO dashboard shipped empty and the alerts never fired,
not because the SLO was met but because the SLI had no data source.

This ADR records what nginx-exporter actually produces on OSS, the
decision to wire it in for the metrics it *does* have, and the explicit
retraction of the metrics it cannot produce.

## Decision

### Wire in `nginx-exporter` for the connection-level SLI

Add a `nginx-exporter` service (`nginx/nginx-prometheus-exporter:1.3.0`)
to `docker-compose.monitoring.yml` and a `/stub_status` location to
`nginx/default.conf`. Prometheus scrapes it on `:9113`. This populates:

| Metric                       | Type    | Notes                                    |
| ---------------------------- | ------- | ---------------------------------------- |
| `nginx_up`                   | gauge   | 1 if the scrape succeeded                |
| `nginx_connections_active`   | gauge   | current connections                      |
| `nginx_connections_reading`  | gauge   |                                           |
| `nginx_connections_writing`  | gauge   |                                           |
| `nginx_connections_waiting`  | gauge   |                                           |
| `nginx_connections_accepted` | counter | total accepted since start               |
| `nginx_connections_handled`  | counter | total handled since start                |
| `nginx_http_requests_total`  | counter | total requests — **no labels**          |

The `nginx:request_rate_5m` recording rule (`rate(nginx_http_requests_total[5m])`)
and the connections panel in the SLO dashboard now have a real source.

### Retract the latency P99 SLO

`stub_status` exposes no timing data. `nginx-prometheus-exporter`
produces no histogram metrics on OSS nginx. There is no metric to feed
`histogram_quantile(0.99, ...)`. The `SLOLatencyP99Breach` alert and the
latency-percentile panels are removed; the alert_rules.yml carries a
comment explaining why and what would re-enable them.

### Change the availability SLI source

`nginx_http_requests_total` has no `status` label on OSS, so the
"non-5xx ratio" SLI is uncomputable. The availability SLI is changed to
`avg_over_time(probe_success[30d])`, the blackbox exporter's probe of
`/health/live/`. This is an *outage* SLI — it fires when the health
endpoint stops answering, not when a fraction of requests return 5xx.

## Rationale

- **Wire in the exporter anyway.** Even with the OSS limitations, the
  connection-level metrics (`nginx_connections_*`, `nginx_up`) are
  operationally useful — they show whether nginx itself is up and how
  loaded it is. The request-rate counter feeds the dashboard's traffic
  panel. Half a signal is better than none.

- **Do not fake the latency SLO.** A latency SLO backed by no data is
  worse than no latency SLO: it gives false confidence. Better to ship
  the outage-only availability SLO and explicitly defer latency until
  the prerequisite pipeline exists.

- **Blackbox probe is honest.** `probe_success` is a real metric that
  exists today. It measures "did the health endpoint answer 200" — a
  coarse but truthful signal. The trade-off is that a partial failure
  (30% of requests 5xx, health endpoint up) does not trip the SLO; the
  existing `High5xxRate` alert covers that case with a guessed
  threshold.

- **NGINX Plus was not considered.** The whole stack is built on OSS
  nginx for licensing and cost reasons (single VPS, $6/month). NGINX
  Plus would give per-status-code and average-latency metrics, but at
  a license cost that is incompatible with the project's budget.

## Consequences

- **Positive:** `nginx:request_rate_5m` and the connections panel
  populate from a real source. The SLO dashboard is no longer empty
  for the nginx-sourced panels.
- **Positive:** the availability SLI (`probe_success`) is honest and
  fires on real outages.
- **Negative:** no latency SLO. A user who experiences 800ms responses
  will not be alerted by the SLO; the operator must watch the dashboard
  or the existing `High5xxRate` alert (which is a throughput alert, not
  a latency alert). **Resolved by ADR-0035** (same release): promtail's
  metrics pipeline derives a latency histogram from the access log, and
  `SLOLatencyP99Breach` is restored.
- **Negative:** the availability SLI is outage-only. Partial failures
  (some endpoints 5xx, health endpoint up) do not burn the budget.
  **Resolved by ADR-0035**: the same pipeline derives a per-status
  counter, and `SLOHigh5xxRate` now fires on partial 5xx errors.
- **Future:** ~~re-introduce the latency SLO when a log-parsing pipeline
  exists~~ — done in ADR-0035.

## Rollout

1. `nginx-exporter` service added to `docker-compose.prod.yml` (not
   monitoring) with `depends_on: nginx: service_healthy`, so the
   exporter starts only after nginx is up and the DNS name resolves.
2. `/stub_status` location added to `nginx/default.conf`, ACL'd to
   private ranges.
3. `nginx` scrape job added to `monitoring/prometheus.yml`.
4. `monitoring/recording_rules.yml` updated: the two non-existent
   recording rules replaced with three that exist.
5. `monitoring/alert_rules.yml` `stacksmith-slo` group rewritten.
6. `grafana/dashboards/slo.json` rewritten (version 2).
7. ADR-0033 amended in place to reflect the new SLI.
