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
| Availability    | 99.5% — health probe succeeds  | 30d    |

> The latency P99 SLO listed in the first draft of this ADR was **retracted**
> in ADR-0034: the OSS nginx stub_status endpoint exposes no latency data, so
> the SLI could not be computed. A log-parsing pipeline is the prerequisite
> for re-introducing a latency SLO.

### SLIs

- **Availability SLI**: `avg_over_time(probe_success[30d])`, where
  `probe_success` is the blackbox exporter's probe of `/health/live/`.
  This is an *outage* SLI (did the health endpoint answer), not a
  *partial-error* SLI (were any requests 5xx). See ADR-0034 for why
  the per-status-code SLI is not available on OSS nginx.

### Error budget

A 99.5% availability SLO allows 0.5% downtime over 30 days. On a
single VPS that is ~3.6 hours of total outage per month — enough
headroom for a reboot, a backup-restore drill, and one bad deploy.

### Alerts

Two alerts (in `monitoring/alert_rules.yml`):

1. **`SLOAvailabilityDown`** (critical) — `probe_success` averaged over
   2m below 0.5. An active outage is burning the budget ~22x faster
   than allowed. Page.
2. **`SLOErrorBudgetExhausted`** (warning) — 30d availability below
   the 99.5% SLO. The budget is gone; deploys should slow down.

### Dashboard

`grafana/dashboards/slo.json` — six panels:

- Availability %, 30d (stat, threshold-colored)
- Error budget used ratio, 0→1 (stat)
- Request rate, req/s (stat, from nginx-exporter)
- Availability probe, 5m average (timeseries)
- Request rate through nginx, 5m (timeseries)
- nginx connections: active/reading/writing/waiting (timeseries)

## Rationale

- **99.5%, not 99.9%.** A single VPS has no redundancy. A 99.9% SLO (43
  min/month downtime) is not honest for a single-machine deployment.
  99.5% (3.6h/month) leaves room for a reboot, a backup restore drill,
  and a bad deploy.

- **blackbox probe as the SLI source, not nginx 5xx.** The first draft
  of this ADR picked "non-5xx ratio" as the availability SLI, assuming
  nginx-exporter would expose per-status-code counts. It does not — the
  OSS stub_status page reports only a total request counter, with no
  `status` label. ADR-0034 records that finding and the decision to
  use the blackbox probe of `/health/live/` as the SLI instead. The
  probe catches outages and hard failures (nginx down, app down, port
  refused), not partial 5xx errors from a misbehaving endpoint. That
  is a coarser SLO, but it is an *honest* SLO.

- **30d window for budget, 2m for burn.** The 30d window gives a stable
  budget number. The 2m window catches active incidents fast — an
  outage burning the budget 22x faster than allowed pages on-call.

## Consequences

- **Positive:** the operator can now answer "how available is the
  service?" with a number, and can justify slowing down deploys when
  the budget is low.
- **Positive:** the fast-burn alert (`SLOAvailabilityDown`) pages
  within 2 minutes of an outage, instead of waiting for the existing
  `AppHealthProbeFailing` 5m window.
- **Negative (retracted):** the latency P99 SLO and the per-status-code
  availability SLI from the first draft are removed — see ADR-0034. The
  dashboard's latency percentile panels were replaced with connection
  counters that stub_status actually produces.
- **Negative:** the SLI is now an *outage* SLI, not a *quality* SLI. A
  deploy that returns 500 for 30% of requests but keeps the health
  endpoint alive would not trip the SLO. The high-5xx alert
  (`High5xxRate`) remains in `stacksmith-availability` for the partial
  failure case, but its threshold is a guess (0.1 req/s), not tied to
  the SLO budget.
- **Negative:** the 30d window means a new deployment does not move the
  budget fast. An operator who deploys 5 times in a day and each deploy
  adds 30s of downtime will not see the budget drop fast. The
  fast-burn alert is the real signal; the budget is the report.

## Rollout

1. Merge this ADR + alert rules + dashboard (this PR).
2. The SLO alerts fire on the existing Alertmanager routing — critical
   to Slack `#alerts`, warning to `#alerts-warn`.
3. The dashboard auto-provisions via the Grafana dashboards provider.
4. The nginx-exporter service is wired into `docker-compose.monitoring.yml`
   in the same PR (ADR-0034) — without it, `nginx:request_rate_5m` is
   empty and only the availability panels (blackbox) populate.
   so the SLI metrics are populated.
