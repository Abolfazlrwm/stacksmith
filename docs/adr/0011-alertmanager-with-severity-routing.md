# ADR-0011: Alertmanager with severity-based routing

- **Status:** accepted
- **Date:** 2026-11-16
- **Supersedes:** the "alerts fire but nobody is paged" gap in the v0.3 roadmap

## Context

v0.2.0 ships Prometheus alert rules (backup staleness, disk saturation,
restart storms, health probe failure, 5xx rate) and a `BackupStale` alert
that has real data (ADR-0006). But the alerts fire inside Prometheus and
go nowhere — there is no Alertmanager, no notification pipeline, no
receiver. An operator has to notice the Grafana dashboard turning red.

The v0.3 roadmap (issue #20) lists "Alert routing" as the first item.

## Decision

Add Alertmanager to the monitoring overlay. Prometheus sends firing alerts
to Alertmanager; Alertmanager routes them by severity:

- **critical** — page immediately (Slack + email), repeat every 1h.
- **warning** — wait 30m, then notify Slack only, repeat every 4h.
- **resolved** — send a follow-up to whichever receiver got the firing
  alert.

Receivers are read from `.env`: `SLACK_WEBHOOK_URL` and `ALERT_EMAIL_TO`.
If a receiver's env var is empty, Alertmanager drops it silently — the
operator enables only the channels they use.

## Rationale

- **Alerts without routing are dashboards with extra steps.** A red panel
  in Grafana is not an incident response. Alertmanager closes the loop:
  firing → notify → ack → resolved.
- **Severity-based routing is the right granularity.** Disk at 85% is a
  warning (fix it today); backup stale at 26h is critical (fix it now).
  Routing both to the same channel at the same urgency is noise.
- **Inhibit the warning when the critical fires.** If `HostDiskFull`
  (critical) and `HostDiskFullWarning` both fire for the same disk, only
  the critical pages. The `inhibit_rules` block handles this.
- **Receivers from env, not from the config file.** The Slack webhook URL
  and email address are secrets. They go in `.env` (git-ignored), not in
  `monitoring/alertmanager.yml` (version-controlled). Alertmanager's
  `$ENV_VAR` substitution reads them at startup.
- **Tested end to end.** The `alerts-drill` workflow posts a synthetic
  alert to Alertmanager's API and verifies a local webhook receiver gets
  the notification. This proves the routing pipeline, not just that
  Alertmanager starts.

## Considered alternatives

### Prometheus direct notifications (no Alertmanager)

Rejected. Prometheus can send alerts to Slack via a webhook receiver, but
it has no grouping, no inhibition, no silencing, and no escalation. Every
firing alert is a separate notification. Alertmanager is purpose-built
for this and is a single container.

### Grafana OnCall / Grafana Alerting

Rejected. Grafana's built-in alerting is excellent but ties alerting to
the Grafana instance — if Grafana is down, alerts do not fire. Prometheus

- Alertmanager is independent of Grafana; Grafana is just a viewer.

### PagerDuty / Opsgenie as the primary receiver

Not rejected, but not the default. The operator can point
`SLACK_WEBHOOK_URL` at a PagerDuty Slack integration, or extend
`alertmanager.yml` with a `pagerduty_configs` receiver. The default is
Slack + email because they are free and universal; paid integrations are
an operator choice, not a framework decision.

### Discord / Telegram webhooks

Not shipped by default. The operator can add a `webhook_configs`
receiver for any platform. The framework ships Slack + email because they
cover the majority of teams; other receivers are a config edit away.

## Consequences

- `docker-compose.monitoring.yml` gains an `alertmanager` service on
  port 9093 (localhost only). It reads `monitoring/alertmanager.yml`.
- `monitoring/prometheus.yml` gains an `alerting` block pointing at
  `alertmanager:9093`.
- `.env.example` gains `SLACK_WEBHOOK_URL` and `ALERT_EMAIL_TO`. Both
  default to empty (receivers disabled).
- `alerts-drill` workflow posts a synthetic critical alert and verifies
  a webhook receiver gets it within 30s.
- The operator must set `SLACK_WEBHOOK_URL` in `.env` before alerts are
  delivered. Without it, alerts fire in Prometheus and are visible in
  the Alertmanager UI (`:9093`) but are not pushed anywhere.
- This decision closes the "Alert routing" item from the v0.3 roadmap
  (issue #20).
