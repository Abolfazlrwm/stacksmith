# StackSmith

[![lint](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/lint.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/lint.yml)
[![smoke](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/smoke.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/smoke.yml)
[![restore drill](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/restore-drill.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/restore-drill.yml)
[![disaster recovery](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/disaster-recovery-drill.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/disaster-recovery-drill.yml)
[![latency SLI](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/latency-sli-drill.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/latency-sli-drill.yml)
[![cosign at deploy](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/cosign-at-deploy.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/cosign-at-deploy.yml)
[![security](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/codeql.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/codeql.yml)
[![unit](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/unit.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/unit.yml)
[![Release](https://img.shields.io/github/v/release/Abolfazlrwm/stacksmith?sort=semver)](https://github.com/Abolfazlrwm/stacksmith/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**deploys this ← [docubot](https://github.com/Abolfazlrwm/docubot)**

## What this is

**docubot** is a self-hosted document-chat platform: upload PDFs,
Markdown, and plain-text documents, then ask questions of them in a
chat interface. Answers are grounded in your own documents via
retrieval-augmented generation (RAG) over a `pgvector` index — no data
leaves your machine, and there is no per-seat cloud lock-in. It is
for small teams and individuals who want the convenience of a chat
assistant over their private corpus without handing their files to a
third party.

**StackSmith** is the production deployment kit for docubot: a single
VPS, no Kubernetes, no cloud lock-in — everything runs on one machine
you can ssh into. It packages the app with nginx, Postgres, Redis, a
full observability stack (Prometheus, Loki, Tempo, Alertmanager,
Grafana), encrypted off-host backups, blue-green deploys, signed
images, and the runbooks + SLOs that make it operable.

> **v1.2.0 — the product catches up to the operations.** Through
> v1.1.x the `app/` directory was a Django health-check stub; the deck
> and this README described a document-chat product that did not exist
> in code. v1.2.0 ships that product. See ADR-0036.

## Product features (docubot)

- **Document chat** — ask questions of your uploaded documents; answers
  cite the source passages.
- **RAG over pgvector** — semantic search of your corpus using
  Postgres-native vector storage; no separate vector DB to run.
- **Multi-format ingestion** — PDF, Markdown, plain text.
- **Self-hosted** — your documents never leave your machine. The LLM
  call is the only outbound request, and you choose the provider.
- **Multi-user** — per-user document collections and chat history.
- **Open source** — MIT licensed, no proprietary runtime.

## Operational features (StackSmith)

- **Zero-downtime deploy** — blue/green via docker-compose, with
  canary probes and auto-rollback (proven in CI).
- **Encrypted backups** — `pg_dump` → age encryption → off-host copy,
  with restore + integrity drills.
- **Disaster recovery** — total VPS loss → encrypted restore → verify
  data and app (proven in CI).
- **Full observability** — metrics (Prometheus), logs (Loki), traces
  (Tempo), alerts (Alertmanager, six dashboards).
- **SLOs** — 99.5% availability over 30d, P99 latency < 500ms, 5xx
  ratio < 2% (ADR-0033, ADR-0035).
- **Security** — CodeQL, Trivy, dependency review, SBOM, cosign image
  signing + verify gate.
- **Infrastructure as code** — Terraform for Hetzner + DigitalOcean.

## Stability

v1.0.0 declared the operational surface stable (ADR-0031); v1.1.x
adds the SLO/SLI layer:

| Surface | Commitment |
|---|---|
| Scripts (`deploy.sh`, `backup-db.sh`, etc.) | CLI is stable; no breaking changes in v1.x |
| Compose (`docker-compose.prod.yml`) | Service names and volumes are stable |
| CI workflows (28) | No workflow removed without a replacement |
| ADRs (30) | No ADR reversed without a superseding ADR |

## Maturity model

| Capability | Status | Proof |
|---|---|---|
| Zero-downtime deploy | ✅ shipped | deploy + rollback drill, canary failure drill |
| Encrypted backups | ✅ shipped | encryption drill, restore drill |
| Disaster recovery | ✅ shipped | total VPS loss drill (destroy → restore → verify) |
| Observability | ✅ shipped | metrics, logs, traces, alerts (5 CI drills) |
| SLO / error budget | ✅ shipped | 99.5% availability, latency + 5xx alerts (ADR-0033, ADR-0035) |
| Security scanning | ✅ shipped | CodeQL, Trivy, dependency review, SBOM |
| Supply chain | ✅ shipped | multi-arch GHCR, cosign sign + verify, build provenance |
| TLS automation | ✅ shipped | certbot renewal loop |
| Secret rotation | ✅ shipped | rotation drill (key + password, zero downtime) |
| Load testing | ✅ shipped | k6 on `/health/live/` (50 VUs, p95 < 500ms) and on `/api/chat/` (10 VUs, p95 < 2.5s, end-to-end RAG) |
| Chaos engineering | ✅ shipped | kill worker + stop nginx → verify recovery |
| Infrastructure as code | ✅ shipped | Terraform (Hetzner + DigitalOcean) |
| Maintenance mode | ✅ shipped | nginx 503 + health probes stay 200 |
| Capacity planning | ✅ shipped | disk exhaustion prediction dashboard |
| Audit trail | ✅ shipped | JSON-lines log for deploy/rollback/restore/backup |
| Document chat (the product) | ✅ shipped | upload → RAG over pgvector → chat with citations; `make demo` proves it end-to-end |
| cosign verify at deploy time | ✅ shipped | `scripts/test_deploy_verify.sh` proves all three branches of the deploy-time gate |
| Multi-host HA | 📋 evaluated | ADR-0015 (not shipped; reopens when traffic requires) |

## Quick start

```bash
git clone https://github.com/Abolfazlrwm/stacksmith.git
cd stacksmith
cp .env.example .env          # fill in the required values
make doctor                   # verify the host is ready
make up                       # bring the stack up
bash scripts/stacksmith-health.sh  # one-command health check
make demo                     # ingest the sample corpus + ask a question
make backup                   # take a database backup
```

For the full walkthrough (TLS, dashboards, blue-green, backup/restore),
see [docs/getting-started.md](docs/getting-started.md).

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
- **Latency SLI drill** — nginx JSON access log → promtail → prometheus
  → recording rules → SLO alerts loaded
- **SLO metrics drill** — nginx-exporter up, availability SLI, alert
  rules loaded
- **Load test** — k6 on `/health/live/` (50 VUs, p95 < 500ms)
- **Chat load test** — k6 on `POST /api/chat/` end-to-end (10 VUs, p95 < 2.5s, RAG + citations)
- **cosign at deploy** — unit test for all three branches of the deploy-time verify gate
- **CodeQL** — semantic code analysis
- **Trivy** — container CVE scan
- **SBOM** — syft + grype
- **Registry build** — multi-arch (amd64 + arm64) GHCR push
- **cosign sign + verify** — keyless signing, SBOM attestation

## Known limitations

See [docs/known-limitations.md](docs/known-limitations.md).

## Architecture

See [docs/architecture.md](docs/architecture.md) for five Mermaid
diagrams (topology, CI pipeline, deploy sequence, backup/DR flow,
firewall rules).

See [docs/api/health-openapi.json](docs/api/health-openapi.json) for the
OpenAPI 3.0 spec.

## Architecture decisions (30 ADRs)

ADR numbers are non-contiguous — gaps (0021/22, 0024, 0026/27, 0029)
are drafts that were merged into adjacent ADRs before publication and
are intentionally not renumbered. See
[docs/adr/INDEX.md](docs/adr/INDEX.md) for the status of each.

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
- [ADR-0020: cosign, terraform, chaos](docs/adr/0020-cosign-and-terraform-and-chaos.md)
- [ADR-0023: cosign verify and disaster recovery](docs/adr/0023-cosign-verify-and-disaster-recovery.md)
- [ADR-0025: deploy verify automation cost](docs/adr/0025-deploy-verify-automation-cost.md)
- [ADR-0028: multi-provider and architecture](docs/adr/0028-multi-provider-and-architecture.md)
- [ADR-0030: operational excellence](docs/adr/0030-operational-excellence.md)
- [ADR-0031: v1.0.0 stability declaration](docs/adr/0031-v1.0.0-stability-declaration.md)
- [ADR-0032: enforce conventional commits](docs/adr/0032-enforce-conventional-commits.md)
- [ADR-0033: SLO, SLI, and error budget](docs/adr/0033-slo-sli-error-budget.md)
- [ADR-0034: nginx exporter and the OSS latency gap](docs/adr/0034-nginx-exporter-and-oss-latency-gap.md)
- [ADR-0035: latency and 5xx SLI from promtail metrics pipeline](docs/adr/0035-latency-sli-from-promtail-metrics.md)
- [ADR-0036: docubot — real product surface, not a health-check stub](docs/adr/0036-docubot-real-product-surface.md)

## Runbooks

- [Operations](docs/runbooks/operations.md) — daily, weekly, incident paths
- [Deploy](docs/runbooks/deploy.md) — normal and rollback paths
- [Backup and restore](docs/runbooks/backup-and-restore.md)
- [Failure playbook](docs/runbooks/failure-playbook.md) — disk full, OOM,
  cert expiry, pg fail, nginx fail

## Layout

```text
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
├── grafana/                      # 6 provisioned dashboards
├── terraform/                    # multi-provider VPS provisioning
├── deploy/systemd/               # backup timer + service units
└── docs/
    ├── adr/                      # 30 ADRs
    ├── runbooks/                 # 4 runbooks
    ├── architecture.md           # 5 Mermaid diagrams
    ├── api/                      # OpenAPI 3.0 spec
    └── known-limitations.md
```

## License

[MIT](LICENSE)
