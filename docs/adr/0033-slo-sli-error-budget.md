# ADR-0033: SLO, SLI, and error budget

- **Status:** accepted
- **Date:** 2026-12-18
- **Supersedes**: —

## Context

v1.0.1 enforces commits and v1.0.0 declared the operational surface
stable. But stability is a feeling without numbers. The kit has alerts
for CPU, disk, memory, backup freshness, and high 5xx rate — but no
service-level objective that says *how available* the service is
supposed to be, and no error budget that says *how much unreliability
is allowed*.

Without an SLO:

- An operator cannot tell whether a 0.3% 5xx rate is fine (it is, if
  the SLO is 99.5%) or a fire (if the SLO is 99.9%).
- A deploy that adds 1% of 5xx for 10 minutes looks the same as a
  full outage in the alert stream.
- There is no number to report to stakeholders.

## Decision

Adopt an availability SLO and a latency SLO, backed by SLIs scraped from
nginx, and alert on error-budget burn.

### SLOs

| SLO             | Target                          | Window |
| --------------- | ------------------------------- | ------ |
| Availability    | 99.5% of requests non-5xx       | 30d    |
| Latency P99     | < 500ms for 99% of requests     | 5m     |

### SLIs

- **Availability SLI**: `1 - (5xx / total)` over the window.
- **Latency SLI**: `histogram_quantile(0.99, nginx_http_request_duration_seconds_bucket)`.

### Error budget

A 99.5% availability SLO allows 0.5% of requests to be 5xx over 30
days. On a single VPS doing ~1 req/s that is ~13,000 allowed failures
per month, or ~3.6 hours of total outage if all requests fail.

### Alerts

Two burn-rate alerts (in `monitoring/alert_rules.yml`):

1. **`SLOErrorBudgetBurnFast`** (critical) — 5xx ratio > 2% for 2m.
   This burns the budget 14x faster than allowed. Page.
2. **`SLOErrorBudgetExhausted`** (warning) — 30d 5xx ratio > 0.5%.
   The budget is gone; deploys should slow down.
3. **`SLOLatencyP99Breach`** (warning) — P99 > 500ms for 5m.

### Dashboard

`grafana/dashboards/slo.json` — six panels:

- Availability % (stat, threshold-colored)
- Error budget remaining in hours (stat)
- P99 latency (stat)
- Request rate by status class (timeseries)
- 5xx ratio with the 2% fast-burn line (timeseries)
- Latency percentile bands p50/p95/p99 (timeseries)

## Rationale

- **99.5%, not 99.9%.** A single VPS has no redundancy. A 99.9% SLO (43
  min/month downtime) is not honest for a single-machine deployment.
  99.5% (3.6h/month) leaves room for a reboot, a backup restore drill,
  and a bad deploy.

- **nginx as the SLI source.** nginx sees every request, including the
  ones that never reach the app (502, 504). App-internal metrics would
  miss the proxy failures.

- **30d window for budget, 5m for burn.** The 30d window gives a stable
  budget number. The 5m window catches active incidents fast. This is the
  standard multi-window multi-burn-rate pattern from the Google SRE
  workbook, simplified to two alerts.

- **Latency SLO is a warning, not critical.** Slow is bad but not the
  same as down. The alert pages the on-call only if it persists.

## Consequences

- **Positive:** the operator can now answer "how available is the
  service?" with a number, and can justify slowing down deploys when the
  budget is low.
- **Positive:** the fast-burn alert catches a bad deploy within 2 minutes
  instead of waiting for the high-5xx alert's 5m window.
- **Negative:** the SLI depends on `nginx_http_requests_total` and
  `nginx_http_request_duration_seconds_bucket` being scraped. If nginx
  does not export these (e.g. the stub_status exporter is not
  configured), the SLO panels are empty. This is a known limitation
  until the nginx exporter is wired into the compose file.
- **Negative:** the 30d window means a new deployment does not move the
  budget much. An operator who deploys 5 times in a day and each deploy
  adds 30s of 5xx will not see the budget drop fast. The fast-burn alert
  is the real signal; the budget is the report.

## Rollout

1. Merge this ADR + alert rules + dashboard (this PR).
2. The SLO alerts fire on the existing Alertmanager routing — critical
   to Slack `#alerts`, warning to `#alerts-warn`.
3. The dashboard auto-provisions via the Grafana dashboards provider.
4. A future PR wires the nginx exporter into `docker-compose.prod.yml`
   so the SLI metrics are populated.
