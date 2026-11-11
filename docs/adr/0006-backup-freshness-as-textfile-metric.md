# ADR-0006: Backup freshness as a textfile metric, not a log line

- **Status:** accepted
- **Date:** 2026-11-10
- **Supersedes:** the v0.1.0 gap documented in `docs/known-limitations.md`

## Context

v0.1.0 shipped a `BackupStale` alert in `monitoring/alert_rules.yml` that
referenced `node_textfile_mtime_seconds{file="backup.prom"}` — a metric
that `backup-db.sh` never wrote. The alert was correct in spirit (fire
when no backup has happened in 26 hours) but had no data to evaluate
against. This was the single biggest gap between claim and reality in the
v0.1.0 release.

## Decision

`backup-db.sh` writes a Prometheus textfile metric
(`monitoring/textfile/backup.prom`) after every successful backup. The
metric exposes three gauges:

- `backup_last_success_timestamp_seconds` — Unix timestamp of the last
  successful backup. Drives the `BackupStale` alert.
- `backup_last_success_bytes` — size of the last backup in bytes. Lets
  the dashboard chart backup growth over time.
- `backup_last_status` — 1 if the last run succeeded, 0 otherwise. Drives
  a new `BackupFailed` alert that fires within 5 minutes of a failure,
  instead of waiting 26 hours for the staleness alert.

node-exporter is already configured (Phase 4) with
`--collector.textfile.directory=/textfile` and the `monitoring/textfile/`
directory is already mounted into the node-exporter container, so no
compose changes are needed.

## Rationale

- **A backup that is not monitored is not a backup.** The operator must
  know within hours, not days, that the nightly backup stopped running.
  A metric + alert is the standard way to deliver that.
- **Textfile is the right transport.** node-exporter's textfile collector
  is designed for exactly this: a script writes a `.prom` file, the
  collector exposes it. No custom exporter, no extra port, no extra
  service.
- **Three gauges, not one.** Timestamp alone tells you "a backup
  happened", but not whether it succeeded, how big it was, or whether it
  is shrinking (a sign of data loss). Three gauges answer all three
  questions on the dashboard.
- **Failure alert separate from staleness.** `BackupStale` fires at 26
  hours — far too late if the backup job crashed at 03:00. `BackupFailed`
  fires at 5 minutes, the moment the metric flips to 0.

## Considered alternatives

### Push the metric to pushgateway

Rejected. Pushgateway is for batch jobs that do not have a long-lived
exporter. We have node-exporter running on the host; the textfile
collector is simpler and does not add a stateful component to prune.

### A dedicated backup-exporter service

Rejected. A whole container to expose three gauges is overkill. The
textfile approach reuses the existing node-exporter.

### Log-based alerting (grep the backup log)

Rejected. Logs are the secondary signal (ADR-0004). A backup failure is
a metric event, not a log event — it has a number (timestamp, size,
status) and it drives an alert. Log-based alerting is brittle (the
matching string changes) and noisy (every run logs multiple lines).

## Consequences

- `backup-db.sh` writes `monitoring/textfile/backup.prom` on every run.
  The write is atomic (write to a temp file, then `mv`).
- `BackupStale` alert now has real data. It fires when
  `time() - backup_last_success_timestamp_seconds > 93600` (26h).
- A new `BackupFailed` alert fires when `backup_last_status == 0` for 5m.
- The restore-drill workflow verifies the metric file is written and the
  gauges are non-zero. This closes the v0.1.0 gap in CI.
- If `backup-db.sh` crashes before writing the metric, the previous
  metric file remains (the last successful backup's values). The
  `BackupStale` alert will eventually fire if no new backup succeeds.
- This decision closes the "backup-freshness metric" item from the v0.2
  roadmap (issue #12).
