# Changelog

All notable changes to stacksmith are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres
to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.8.0] — 2026-12-11

Multi-provider infrastructure, architecture documentation, API specification.

### Added

- **Phase 12.1** — Multi-provider Terraform. Hetzner Cloud + DigitalOcean
  in one module, selected by `provider` variable. ADR-0028.
- **Phase 12.2** — Architecture documentation. Five Mermaid diagrams
  (topology, CI pipeline, deploy sequence, backup/DR flow, firewall) plus
  service and observability inventory tables.
- **Phase 12.3** — OpenAPI 3.0 spec for the health endpoints
  (`/health/live/`, `/health/ready/`) with response schemas. ADR-0029.

## [0.7.0] — 2026-12-08

Deploy-time security, developer automation, and cost visibility.

### Added

- **Phase 11.1** — Deploy-time cosign verify. `deploy.sh` verifies the
  image signature before switching the upstream. Hard abort on failure.
  ADR-0025.
- **Phase 11.2** — Release drafter. Maintains a draft GitHub Release from
  PR titles and labels. Dependabot auto-merge for patch and minor bumps
  after CI passes; major bumps get `needs-review`. ADR-0026.
- **Phase 11.3** — Cost monitoring dashboard. `cost-metric.sh` writes a
  textfile metric; Grafana panel shows monthly cost, CPU/memory/disk, and
  per-service cost breakdown. ADR-0027.

## [0.6.0] — 2026-12-04

Operational maturity: the kit now proves it can survive a total VPS loss
and verifies its own supply chain end to end.

### Added

- **Phase 10.1** — cosign verify gate. A CI workflow verifies the image
  signature and SBOM attestation on every push to main and daily at 06:00
  UTC. Also fixes cosign-sign timing (workflow_run on registry-build
  completed). ADR-0023.
- **Phase 10.2** — Disaster recovery drill. Six-phase total VPS loss
  simulation: seed data, encrypt backup, destroy everything (containers +
  volumes + plaintext), provision fresh stack, restore from encrypted .age,
  verify data values + app health. ADR-0024.
- **Phase 10.3** — Automated release notes. Generates changelog sections
  from conventional commits when a tag is pushed.
- **Phase 10.4** — Stale bot. Closes issues inactive for 37 days and PRs
  inactive for 21 days. Exempts pinned and roadmap labels.

### Proven in CI (21 workflows)

All previous 17 plus:
- cosign verify (signature + SBOM attestation)
- disaster recovery drill (total VPS loss)
- stale bot (daily)
- release notes (on tag)

## [0.5.0] — 2026-11-30

Supply chain, infrastructure as code, and chaos engineering.

### Added

- **Phase 9.1** — Multi-arch registry images. Multi-stage Dockerfile,
  linux/amd64 + linux/arm64 builds via Buildx + QEMU, GHCR push with SHA
  tags, build provenance attestation (SLSA L3). ADR-0019.
- **Phase 9.2** — cosign keyless image signing. Signs the GHCR image
  with GitHub OIDC identity, attaches SBOM as a cosign attestation,
  verifies immediately. ADR-0020.
- **Phase 9.3** — Terraform VPS provisioning. Hetzner Cloud VPS,
  firewall, cloud-init that installs Docker and clones the repo. ADR-0021.
- **Phase 9.4** — Chaos engineering drill. Kills the worker, verifies the
  app survives, stops nginx, verifies the outage, restarts both. ADR-0022.

### Proven in CI (20 workflows)

- lint, smoke (stub + prod), deploy + rollback drill, canary failure,
  restore drill, encryption drill, integrity drill, rotation drill,
  logs drill, alerts drill, tracing drill, CodeQL, Trivy, SBOM, k6,
  registry build (multi-arch), cosign sign, chaos drill

## [0.4.0] — 2026-11-25

Production hardening: the kit now proves its supply chain is clean and
its performance is bounded.

### Added

- **Phase 8.1** — Automated security scanning. CodeQL (semantic code
  analysis), Trivy (container image CVE scan, SARIF to Security tab),
  dependency review (PR gate for vulnerable dependency bumps). ADR-0016.
- **Phase 8.2** — SBOM generation. syft produces SPDX JSON and CycloneDX
  JSON bills of materials for the app image; grype scans the SBOM for
  known vulnerabilities. All artifacts uploaded with 30-day retention.
  ADR-0017.
- **Phase 8.3** — Load testing with k6. A 70-second load test ramps to
  50 VUs and enforces p95 < 500ms and failure rate < 1%. A regression
  that breaches the thresholds fails CI. ADR-0018.
- **Phase 8.4** — Community files. Feature request issue template, pull
  request template, CODEOWNERS.

### Proven in CI (17 workflows)

- lint (yamllint, shellcheck, compose config)
- smoke (stub + prod)
- deploy + rollback drill
- canary failure → auto-rollback
- restore drill + metric verification
- encryption drill
- integrity drill
- rotation drill
- logs drill (Loki)
- alerts drill (Alertmanager)
- tracing drill (Tempo)
- CodeQL
- Trivy container scan
- SBOM generation (syft + grype)
- k6 load test

### Security posture

- CodeQL scans the Python code weekly and on every push.
- Trivy scans the built image and uploads SARIF to the Security tab.
- Dependency review blocks PRs that introduce MODERATE+ vulnerabilities.
- SBOM is generated in SPDX and CycloneDX formats on every push.
- Grype scans the SBOM for known vulnerabilities.

## [0.3.0] — 2026-11-20

The v0.3 roadmap is closed. Every item from issue #20 ships in this release.

### Added

- **Phase 7.1** — Alertmanager with severity-based routing. Critical alerts
  page immediately (Slack), warnings wait 30m. Prometheus sends to
  Alertmanager; the `alerts-drill` CI proves a synthetic alert reaches a
  webhook receiver. ADR-0011.
- **Phase 7.2** — Backup integrity verification. `verify-backup.sh` restores
  a backup into a throwaway database and diffs row counts of every table
  against the source. The `integrity-drill` CI seeds multiple tables and
  verifies the counts match. ADR-0012.
- **Phase 7.3** — Secret rotation automation. `rotate-secrets.sh` rotates
  `DJANGO_SECRET_KEY` (via deploy) and `POSTGRES_PASSWORD` (via ALTER USER +
  restart) with zero downtime. The `rotation-drill` CI rotates both and
  verifies the stack stays healthy. ADR-0013.
- **Phase 7.4** — Distributed tracing with OpenTelemetry and Tempo. The
  Django app is auto-instrumented (Django, psycopg, redis, celery); traces
  export to Tempo over OTLP/HTTP. Grafana gains a Tempo datasource with
  traces-to-logs and traces-to-metrics links. The `tracing-drill` CI
  generates traces and queries Tempo. ADR-0014.
- **Phase 7.5** — Multi-host readiness evaluation. ADR-0015 documents what
  it would take to move to two hosts (managed Postgres/Redis, load balancer,
  rolling deploys) and when the decision should be reopened.

### Proven in CI (14 jobs)

- `lint` — yamllint, shellcheck, docker compose config
- `smoke` (stub) — nginx + static health page
- `smoke` (prod) — full stack up, health probes through nginx
- `deploy + rollback drill` — blue → green → blue with canary probes
- `canary failure → auto-rollback` — break app-green, verify auto-rollback
- `backup → wipe → restore → verify` — restore drill + metric verification
- `encrypt → decrypt → restore → verify` — encryption drill
- `backup → verify → row counts match` — integrity drill
- `rotate key → app still serves → rotate password → app still serves`
- `loki ready → ingest → query` — logs drill
- `alertmanager → webhook → verify delivery` — alerts drill
- `tempo ready → trace → query` — tracing drill

### Closed roadmap items (issue #20)

- [x] Alert routing (ADR-0011)
- [x] Backup integrity verification (ADR-0012)
- [x] Secret rotation automation (ADR-0013)
- [x] Distributed tracing (ADR-0014)
- [x] Multi-host readiness (ADR-0015 — evaluation, not action)

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
