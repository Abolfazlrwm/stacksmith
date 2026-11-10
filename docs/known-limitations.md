# Known limitations

What works today is proven in CI. What does not is listed here, honestly.

## Not implemented

- **TLS is a template.** The `:443` server block in `nginx/default.conf`
  is commented out. To enable HTTPS, obtain a cert, place it in
  `nginx/certs/`, uncomment the block, and reload nginx. There is no
  automated cert renewal pipeline.
- **No log aggregation.** Logs are json-file on each container, read with
  `docker compose logs`. There is no Loki, Elasticsearch, or equivalent.
  ADR-0004 explains why; Loki is on the v0.2 roadmap.
- **No canary checks post-switch.** `deploy.sh` switches 100% of traffic
  to the new color immediately. There is no 1%-then-10%-then-100% ramp.
  Canary checks are on the v0.2 roadmap.
- **No off-host encryption.** `sync-backups.sh` copies dumps over rsync
  as-is. The dumps are not encrypted at rest on the off-host. Off-host
  encryption with `age` is on the v0.2 roadmap.
- **Single host.** Everything runs on one VPS. There is no HA, no
  multi-host failover, no horizontal scaling. ADR-0001 documents this as
  a deliberate choice.
- **No automated secret rotation.** Secret rotation is a manual procedure
  documented in ADR-0005. There is no cron job or operator that rotates
  keys on a schedule.
- **Grafana is not exposed through nginx.** Grafana listens on port 3000
  directly. In production, it should be behind nginx with auth; for now,
  restrict it with a firewall.

## Recently closed

- **Backup freshness metric** (closed 2026-11-10, ADR-0006).
  `backup-db.sh` now writes `monitoring/textfile/backup.prom` with three
  gauges (`backup_last_success_timestamp_seconds`,
  `backup_last_success_bytes`, `backup_last_status`). The `BackupStale`
  and `BackupFailed` alerts evaluate against these gauges. The
  restore-drill workflow verifies the metric file is written and the
  gauges are non-zero.

## Tested but not in production

- The backup and restore scripts are tested in CI against a fresh
  database. They have not been run against a large production database.
  The restore time for a multi-GB dump is unknown.
- The blue-green deploy is tested in CI with a health probe. It has not
  been tested under real traffic with long-lived connections (websockets,
  streaming uploads). The `GRACE_PERIOD` may need tuning.

## Roadmap to v0.2

See issue [#12](https://github.com/Abolfazlrwm/stacksmith/issues/12) for
the planned work. Items still open:

- Off-host encryption with `age`.
- Canary checks post-switch.
- Loki as a secondary observability signal.
- Automated cert renewal.
- Grafana behind nginx with auth.

Items closed:

- `backup.prom` textfile metric written by `backup-db.sh` — closed by
  ADR-0006.
