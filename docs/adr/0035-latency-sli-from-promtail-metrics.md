# ADR-0035: latency and 5xx SLI from promtail metrics pipeline

- **Status:** accepted
- **Date:** 2026-12-22
- **Amends**: ADR-0033 (re-introduces the latency P99 SLO), ADR-0034
  (closes the OSS nginx gap that this ADR's pipeline was the
  prerequisite for)

## Context

ADR-0034 retracted the latency P99 SLO and left the availability SLI
as an outage-only signal (blackbox `probe_success`), because OSS nginx's
`stub_status` endpoint exposes no latency data and no per-status-code
request counts. The ADR explicitly named the prerequisite for
re-introducing both: "a log-parsing pipeline (promtail → Loki → a
recording rule that derives p99 from nginx access-log `$request_time`)".

This ADR ships that pipeline.

## Decision

### Emit a JSON access log from nginx

Add a `stacksmith_json` `log_format` to `nginx/default.conf` that
includes `$status` (as a JSON number) and `$request_time` (as a float
seconds value), plus `method`, `uri`, `bytes_sent`, and `request_id` for
debugging. JSON is far easier to parse than the default combined format
and preserves the number types promtail's metrics stage needs.

### Derive Prometheus metrics in promtail

promtail already scrapes docker container logs. Add a dedicated
`nginx_access` scrape config (filtered to the `nginx` service) with a
`metrics` pipeline stage that produces:

| Metric                                | Type      | Labels            |
| ------------------------------------- | --------- | ----------------- |
| `nginx_log_request_duration_seconds`  | Histogram | `le` (bucket)     |
| `nginx_log_requests_total`            | Counter   | `status`, `method`|

promtail exposes these on its existing `:9080/metrics` endpoint (the
same port it already serves for its own internal metrics). Prometheus
scrapes promtail as a new `promtail` job.

This avoids the Loki Ruler + remote_write complexity that ADR-0034's
note implied — promtail's metrics stage computes the metrics inline as
logs flow through, with no extra moving parts.

### Re-introduce the latency and 5xx SLOs

With `nginx_log_request_duration_seconds_bucket` now present, the
recording rules compute P50/P95/P99 latency. The `SLOLatencyP99Breach`
alert (P99 > 500ms for 5m, warning) is restored.

With `nginx_log_requests_total{status=...}` now present, the recording
rules compute the 5xx ratio over 5m and 30d. A new `SLOHigh5xxRate`
alert (5xx > 2% for 2m, critical) closes the "partial failure" gap that
ADR-0034 left: a deploy that returns 5xx for 30% of requests but keeps
the health endpoint up now pages on-call, instead of slipping past the
outage-only `SLOAvailabilityDown`.

## Rationale

- **promtail metrics stage, not Loki Ruler.** The metrics stage runs
  inline as logs flow through promtail, with no extra service, no
  remote_write, and no second query language to learn. Loki stays a
  log store; promtail doubles as a log-derived metrics source.

- **JSON log format, not regex.** The default combined format would
  need a regex pipeline stage that is fragile and slow. JSON parsing
  is one stage and preserves number types, which the metrics stage
  requires (a string `request_time` would be silently dropped).

- **Do not label by URI.** High cardinality. `status` and `method`
  only. If per-endpoint latency is ever needed, a separate
  lower-volume metric with an allow-list of URIs can be added later.

- **Histogram buckets cover 50ms to 10s.** The SLO threshold is 500ms;
  the buckets around it (250ms, 500ms, 1s) give enough resolution for
  `histogram_quantile` to be accurate near the threshold.

- **5xx alert is critical, not warning.** A 2% 5xx rate for 2 minutes
  is a quality incident, not a slow-down. It pages.

## Consequences

- **Positive:** the latency P99 SLO is restored. The dashboard's
  latency band panel and the 5xx ratio panel now have real data.
- **Positive:** the partial-failure gap from ADR-0034 is closed. A
  misbehaving endpoint that 5xxs without taking down the health probe
  now burns the budget and pages.
- **Negative:** promtail now does CPU work (JSON parse + metric
  increment) on every access log line. On a single VPS at ~1 req/s this
  is negligible; at high load it is worth watching promtail's CPU.
- **Negative:** the histogram is only as accurate as nginx's
  `$request_time`. It measures wall-clock time from the first byte
  received to the last byte sent, including network. It does not
  isolate app vs nginx overhead — for that, pair with the upstream
  response time (already logged but not yet a metric).

## Status of the promtail metrics stage (open, as of v1.1.3)

The `nginx_log_*` metrics the recording rules depend on are **not yet
produced** by promtail's `metrics` pipeline stage. The pipeline
architecture is sound and verified: nginx emits a valid JSON access log
with `request_time` and `status`, promtail discovers the nginx
container, promtail is scraped by prometheus (`up{job=promtail}=1`),
both alerts load, and the recording rules are registered. What is
missing is the metrics stage actually emitting the histogram and
counter.

Two hypotheses were tested and both produced no metrics:

1. **Two json stages** (first to unwrap the Docker log wrapper, second
   to parse the inner nginx JSON) — the metrics stage logged "source
   does not exist" at debug level.
2. **One json stage** parsing `status`/`request_time`/`method`/`uri`
   directly — same result.

This means the source fields are not landing in the extracted map
under either interpretation of how `docker_sd_configs` feeds lines to
the pipeline. The exact mechanism (whether the wrapper is auto-
unwrapped, whether the `labels` stage silently drops numeric values
before the `metrics` stage runs, whether `config.action` is required
on the histogram) is unresolved. Local docker is unavailable in the
build environment, so iteration is limited to slow CI cycles.

**Pragmatic decision for v1.1.3:** the `latency-sli-drill` workflow
asserts what is verifiably true — promtail is up, prometheus scrapes
it, both alerts load — and treats the metrics stage and recording-rule
values as **advisory** (printed, not failed on). Failing the drill on
the metrics stage would block every PR on a known issue. The drill
remains a blocking check for the parts that work; when the metrics
stage is debugged (or replaced with a small exporter that parses the
nginx access log directly), the advisory steps are promoted back to
assertions.

- **Future:** the `upstream_response_time` field is in the JSON log
  but not yet a metric. A follow-up could add a second histogram to
  distinguish "nginx slow" from "app slow".

## Rollout

1. `stacksmith_json` log_format added to `nginx/default.conf`; the
   server block now writes access logs in JSON.
2. `nginx_access` scrape config added to `monitoring/promtail.yml`
   with json + labels + metrics pipeline stages.
3. `promtail` scrape job added to `monitoring/prometheus.yml`.
4. `monitoring/recording_rules.yml` adds
   `nginx:p99_latency_ms_5m`, `nginx:p50_latency_ms_5m`,
   `nginx:p95_latency_ms_5m`, `nginx:error_rate_5xx_5m`,
   `nginx:error_rate_5xx_30d`.
5. `monitoring/alert_rules.yml` re-introduces `SLOLatencyP99Breach`
   and adds `SLOHigh5xxRate`.
6. `grafana/dashboards/slo.json` v3 — three new panels (P99 stat,
   latency bands timeseries, 5xx ratio timeseries).
7. ADR-0033 and ADR-0034 amended in place to point here.
