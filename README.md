# StackSmith

[![lint](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/lint.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/lint.yml)
[![smoke](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/smoke.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/smoke.yml)
[![restore drill](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/restore-drill.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/restore-drill.yml)
[![disaster recovery](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/disaster-recovery-drill.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/disaster-recovery-drill.yml)
[![security](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/codeql.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/codeql.yml)
[![Release](https://img.shields.io/github/v/release/Abolfazlrwm/stacksmith?sort=semver)](https://github.com/Abolfazlrwm/stacksmith/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**deploys this ← [docubot](https://github.com/Abolfazlrwm/docubot)**

Production-grade deployment kit for the docubot stack. One VPS, no
Kubernetes, no cloud lock-in — everything runs on a single machine you
can ssh into.

> **v1.0.0 — stable.** The operational surface (scripts, compose, CI)
> is stable. v1.x patches add features without breaking changes.

## Stability

v1.0.0 declares the operational surface stable (ADR-0031):

| Surface | Commitment |
|---|---|
| Scripts (`deploy.sh`, `backup-db.sh`, etc.) | CLI is stable; no breaking changes in v1.x |
| Compose (`docker-compose.prod.yml`) | Service names and volumes are stable |
| CI workflows (23) | No workflow removed without a replacement |
| ADRs (31) | No ADR reversed without a superseding ADR |

## Maturity model

| Capability | Status | Proof |
|---|---|---|
| Zero-downtime deploy | ✅ shipped | deploy + rollback drill, canary failure drill |
| Encrypted backups | ✅ shipped | encryption drill, restore drill |
| Disaster recovery | ✅ shipped | total VPS loss drill (destroy → restore → verify) |
| Observability | ✅ shipped | metrics, logs, traces, alerts (5 CI drills) |
| Security scanning | ✅ shipped | CodeQL, Trivy, dependency review, SBOM |
| Supply chain | ✅ shipped | multi-arch GHCR, cosign sign + verify, build provenance |
| TLS automation | ✅ shipped | certbot renewal loop |
| Secret rotation | ✅ shipped | rotation drill (key + password, zero downtime) |
| Load testing | ✅ shipped | k6 (50 VUs, p95 < 500ms threshold) |
| Chaos engineering | ✅ shipped | kill worker + stop nginx → verify recovery |
| Infrastructure as code | ✅ shipped | Terraform (Hetzner + DigitalOcean) |
| Maintenance mode | ✅ shipped | nginx 503 + health probes stay 200 |
| Capacity planning | ✅ shipped | disk exhaustion prediction dashboard |
| Audit trail | ✅ shipped | JSON-lines log for deploy/rollback/restore/backup |
| Multi-host HA | 📋 evaluated | ADR-0015 (not shipped; reopens when traffic requires) |
| Business load tests | 📋 planned | only /health/live/ is tested |

## Quick start

```bash
git clone https://github.com/Abolfazlrwm/stacksmith.git
cd stacksmith
cp .env.example .env          # fill in the required values
make doctor                   # verify the host is ready
make up                       # bring the stack up
bash scripts/stacksmith-health.sh  # one-command health check
make backup                   # take a database backup
```

## What works today (proven in CI)

- **Lint** — yamllint, shellcheck, docker compose config
- **Smoke** — stub + prod stack, health probes through nginx
- **Deploy drill** — blue → green → blue with canary probes
- **Canary failure → auto-rollback** — break green, verify rollback
- **Restore drill** — backup → wipe → restore → verify row counts + metric
- **Encryption drill** — encrypt → restore from .age → verify
- **Integrity drill** — row count diff against throwaway database
- **Rotation drill** — rotate key + password, verify still serving
- **Logs drill** — Loki ingest → query
- **Alerts drill** — Alertmanager → webhook delivery
- **Tracing drill** — Tempo ingest → query
- **Chaos drill** — kill worker + stop nginx → verify recovery
- **DR drill** — total VPS loss → encrypted restore → verify data + app
- **Load test** — k6 (50 VUs, p95 < 500ms)
- **CodeQL** — semantic code analysis
- **Trivy** — container CVE scan
- **SBOM** — syft + grype
- **Registry build** — multi-arch (amd64 + arm64) GHCR push
- **cosign sign + verify** — keyless signing, SBOM attestation

## Known limitations

See [docs/known-limitations.md](docs/known-limitations.md).

## Architecture

See [docs/architecture.md](docs/architecture.md) for 5 Mermaid diagrams
(topology, CI pipeline, deploy sequence, backup/DR flow, firewall).

See [docs/api/health-openapi.json](docs/api/health-openapi.json) for the
OpenAPI 3.0 spec.

## Architecture decisions (31 ADRs)

- [ADR-0001: compose as the deployment unit](docs/adr/0001-use-compose-as-the-deployment-unit.md)
- [ADR-0002: blue-green with compose](docs/adr/0002-blue-green-with-compose.md)
- [ADR-0003: dump-based backups over WAL shipping](docs/adr/0003-dump-based-backups-over-wal-shipping.md)
- [ADR-0004: metrics-first, logs-second observability](docs/adr/0004-metrics-first-logs-second-observability.md)
- [ADR-0005: secrets in .env with documented rotation](docs/adr/0005-secrets-in-env-with-documented-rotation.md)
- [ADR-0006: backup freshness as a textfile metric](docs/adr/0006-backup-freshness-as-textfile-metric.md)
- [ADR-0007: off-host encryption with age](docs/adr/0007-off-host-encryption-with-age.md)
- [ADR-0008: canary checks post-switch with auto-rollback](docs/adr/0008-canary-checks-post-switch.md)
- [ADR-0009: Loki as a secondary observability signal](docs/adr/0009-loki-as-secondary-observability.md)
- [ADR-0010: automated TLS with certbot](docs/adr/0010-automated-tls-with-certbot.md)
- [ADR-0011: Alertmanager with severity routing](docs/adr/0011-alertmanager-with-severity-routing.md)
- [ADR-0012: backup integrity verification](docs/adr/0012-backup-integrity-verification.md)
- [ADR-0013: secret rotation with zero downtime](docs/adr/0013-secret-rotation-with-zero-downtime.md)
- [ADR-0014: OpenTelemetry traces to Tempo](docs/adr/0014-opentelemetry-traces-to-tempo.md)
- [ADR-0015: multi-host readiness](docs/adr/0015-multi-host-readiness.md)
- [ADR-0016: automated security scanning](docs/adr/0016-automated-security-scanning.md)
- [ADR-0017: SBOM generation with syft](docs/adr/0017-sbom-generation-with-syft.md)
- [ADR-0018: load testing with k6](docs/adr/0018-load-testing-with-k6.md)
- [ADR-0019: multi-arch registry images](docs/adr/0019-multi-arch-registry-images.md)
- [ADR-0020: cosign image signing](docs/adr/0020-cosign-and-terraform-and-chaos.md)
- [ADR-0021: Terraform provisioning](docs/adr/0020-cosign-and-terraform-and-chaos.md)
- [ADR-0022: chaos engineering drill](docs/adr/0020-cosign-and-terraform-and-chaos.md)
- [ADR-0023: cosign verify gate](docs/adr/0023-cosign-verify-and-disaster-recovery.md)
- [ADR-0024: disaster recovery drill](docs/adr/0023-cosign-verify-and-disaster-recovery.md)
- [ADR-0025: deploy-time cosign verify](docs/adr/0025-deploy-verify-automation-cost.md)
- [ADR-0026: release drafter and Dependabot auto-merge](docs/adr/0025-deploy-verify-automation-cost.md)
- [ADR-0027: cost monitoring dashboard](docs/adr/0025-deploy-verify-automation-cost.md)
- [ADR-0028: multi-provider Terraform](docs/adr/0028-multi-provider-and-architecture.md)
- [ADR-0029: architecture docs and OpenAPI](docs/adr/0028-multi-provider-and-architecture.md)
- [ADR-0030: operational excellence](docs/adr/0030-operational-excellence.md)
- [ADR-0031: v1.0.0 stability declaration](docs/adr/0031-v1.0.0-stability-declaration.md)

## Runbooks

- [Operations](docs/runbooks/operations.md) — daily, weekly, incident paths
- [Deploy](docs/runbooks/deploy.md) — normal and rollback paths
- [Backup and restore](docs/runbooks/backup-and-restore.md)
- [Failure playbook](docs/runbooks/failure-playbook.md) — disk full, OOM, cert expiry, pg fail, nginx fail

## Layout

```
.
├── docker-compose.prod.yml       # the deployment unit
├── docker-compose.monitoring.yml # observability overlay
├── docker-compose.tls.yml        # TLS overlay (certbot)
├── Makefile                      # one entry point for ops
├── scripts/                      # 18 operational scripts
├── app/                          # minimal Django app (health endpoints)
├── nginx/                        # reverse proxy + upstreams + TLS
├── postgres/                     # tuned postgresql.conf
├── monitoring/                   # prometheus, alert + recording rules, blackbox
├── grafana/                      # 5 provisioned dashboards
├── terraform/                    # multi-provider VPS provisioning
├── deploy/systemd/               # backup timer + service units
└── docs/
    ├── adr/                      # 31 ADRs
    ├── runbooks/                 # 4 runbooks
    ├── architecture.md           # 5 Mermaid diagrams
    ├── api/                      # OpenAPI 3.0 spec
    └── known-limitations.md
```

## License

[MIT](LICENSE)
