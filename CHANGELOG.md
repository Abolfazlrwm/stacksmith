# Changelog

All notable changes to stacksmith are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres
to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] — 2026-11-15

The v0.2 roadmap is closed. Every item from issue #12 ships in this release.

### Added

- **Phase 6.1** — `backup-db.sh` writes a `backup.prom` textfile metric
  with three gauges (`backup_last_success_timestamp_seconds`,
  `backup_last_success_bytes`, `backup_last_status`). The `BackupStale`
  alert now has real data; a new `BackupFailed` alert fires at 5m instead
  of 26h. ADR-0006.
- **Phase 6.2** — off-host encryption with `age`. `encrypt-backups.sh`
  encrypts every backup with the public key; `sync-backups.sh` ships only
  `.age` files; `restore-db.sh` accepts `.age` and decrypts in-stream.
  The encryption-drill workflow proves the full cycle. ADR-0007.
- **Phase 6.3** — canary checks post-switch with auto-rollback. `deploy.sh`
  runs `CANARY_PROBES` health probes through nginx after the upstream
  switch; a failed probe rolls back automatically. The canary-failure-drill
  CI job breaks app-green and verifies deploy.sh catches it. ADR-0008.
- **Phase 6.4** — Loki and promtail for log aggregation. Single-node Loki
  with 14-day retention; promtail scrapes docker logs via the socket and
  parses JSON lines for `level` and `name` labels. Grafana gains a Loki
  datasource and a container-logs dashboard. The logs-drill CI workflow
  proves the ingest path. ADR-0009.
- **Phase 6.5** — automated TLS with certbot. `docker-compose.tls.yml`
  runs certbot in a 12h renewal loop with `--deploy-hook` that reloads
  nginx. `scripts/issue-cert.sh` obtains the first Let's Encrypt cert via
  ACME HTTP-01. The `:443` server block is real (in `nginx/tls.conf.disabled`,
  enabled by `issue-cert.sh`). ADR-0010.
- **Phase 6.6** — Grafana behind nginx with basic auth. Grafana is no
  longer exposed on port 3000 directly; it is proxied at `/grafana/` with
  an htpasswd file. `scripts/setup-grafana-auth.sh` generates the htpasswd.

### Proven in CI (10 jobs, all green)

- `lint` — yamllint, shellcheck, docker compose config (including TLS overlay)
- `smoke` (stub) — nginx + static health page
- `smoke` (prod) — full stack up, `/health/live/` and `/health/ready/`
- `deploy + rollback drill` — blue → green → blue with canary probes
- `canary failure → auto-rollback` — break app-green, verify auto-rollback
- `backup → wipe → restore → verify` — restore drill with metric verification
- `encrypt → decrypt → restore → verify` — encryption drill
- `loki ready → ingest → query` — logs drill
- `stub stack` — nginx + static page

### Closed roadmap items (issue #12)

- [x] Off-host encryption with `age`
- [x] Canary checks post-switch
- [x] `backup.prom` textfile metric
- [x] Loki as a secondary observability signal
- [x] Automated cert renewal
- [x] Grafana behind nginx with auth

## [0.1.0] — 2026-11-08

First tagged release. The full deploy → monitor → backup → restore cycle
is implemented and proven in CI.

### Added

- **Phase 0** — repository skeleton, lint + smoke CI, dependabot,
  engineering conventions, ADR-0001 (compose as the deployment unit).
- **Phase 1** — production compose stack: app (gunicorn + Django), worker,
  beat, postgres (pgvector/pg17, tuned config, named volumes), redis,
  nginx (reverse proxy, gzip, security headers, TLS template). Per-service
  healthchecks, `.env.example` + `check-env.sh`, json-file log rotation.
- **Phase 2** — blue-green deploy with nginx upstream switch, one-command
  rollback, immutable release tags with manifest, deploy runbook, ADR-0002.
  CI proves the deploy + rollback cycle is zero-downtime.
- **Phase 3** — nightly `pg_dump` with gzip + sha256 + retention, off-host
  rsync with a lock, one-command restore with pre-flight check, restore
  drill in CI (backup → wipe → restore → verify row counts), ADR-0003,
  systemd timer/service units.
- **Phase 4** — prometheus, node-exporter, cAdvisor, blackbox-exporter,
  grafana with two provisioned dashboards, alert rules (backup staleness,
  disk, memory, restarts, 5xx rate, health probe), ADR-0004.
- **Phase 5** — operations runbook, failure playbook, ADR-0005 (secrets
  rotation), this changelog.

### Known limitations

See `docs/known-limitations.md`. All v0.1.0 limitations are closed in v0.2.0.
