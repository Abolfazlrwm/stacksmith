# ADR index

This is the table of contents for the Architecture Decision Records. Each
ADR records *one* decision: the context, the choice, the alternatives we
rejected, and the consequences we accept.

Numbers are monotonic but not contiguous — gaps (0021, 0022, 0024,
0026, 0027, 0029) are ADRs that were drafted and merged into another
ADR's scope, or superseded before publishing. We do not renumber.

## How to read an ADR

```text
ADR-NNNN: <title>
- Status: accepted | superseded | deferred | proposed
- Date:   YYYY-MM-DD
- Supersedes: ADR-MMMM (if any)

## Context     — the problem and the forces
## Decision    — what we chose
## Rationale   — why, and what we rejected
## Consequences — what we now live with
```

## Index

| #      | Title                                                        | Status    | Date       |
| ------ | ------------------------------------------------------------ | --------- | ---------- |
| 0001   | [docker compose is the deployment unit](0001-use-compose-as-the-deployment-unit.md) | accepted  | 2026-11-03 |
| 0002   | [Blue-green deploys with compose](0002-blue-green-with-compose.md) | accepted  | 2026-11-05 |
| 0003   | [Dump-based backups over WAL shipping](0003-dump-based-backups-over-wal-shipping.md) | accepted  | 2026-11-06 |
| 0004   | [Metrics-first, logs-second observability](0004-metrics-first-logs-second-observability.md) | accepted  | 2026-11-07 |
| 0005   | [Secrets in .env with documented rotation](0005-secrets-in-env-with-documented-rotation.md) | accepted  | 2026-11-08 |
| 0006   | [Backup freshness as a textfile metric](0006-backup-freshness-as-textfile-metric.md) | accepted  | 2026-11-10 |
| 0007   | [Off-host encryption with age](0007-off-host-encryption-with-age.md) | accepted  | 2026-11-11 |
| 0008   | [Canary checks post-switch with auto-rollback](0008-canary-checks-post-switch.md) | accepted  | 2026-11-12 |
| 0009   | [Loki as a secondary observability signal](0009-loki-as-secondary-observability.md) | accepted  | 2026-11-13 |
| 0010   | [Automated TLS with certbot](0010-automated-tls-with-certbot.md) | accepted  | 2026-11-14 |
| 0011   | [Alertmanager with severity routing](0011-alertmanager-with-severity-routing.md) | accepted  | 2026-11-16 |
| 0012   | [Backup integrity verification](0012-backup-integrity-verification.md) | accepted  | 2026-11-17 |
| 0013   | [Secret rotation with zero downtime](0013-secret-rotation-with-zero-downtime.md) | accepted  | 2026-11-18 |
| 0014   | [OpenTelemetry traces to Tempo](0014-opentelemetry-traces-to-tempo.md) | accepted  | 2026-11-19 |
| 0015   | [Multi-host readiness — leaving one VPS](0015-multi-host-readiness.md) | deferred  | 2026-11-20 |
| 0016   | [Automated security scanning](0016-automated-security-scanning.md) | accepted  | 2026-11-21 |
| 0017   | [SBOM generation with syft and grype](0017-sbom-generation-with-syft.md) | accepted  | 2026-11-22 |
| 0018   | [Load testing with k6](0018-load-testing-with-k6.md) | accepted  | 2026-11-23 |
| 0019   | [Multi-arch registry images with GHCR](0019-multi-arch-registry-images.md) | accepted  | 2026-11-26 |
| 0020   | [cosign image signing and SBOM attestation](0020-cosign-and-terraform-and-chaos.md) | accepted  | 2026-11-27 |
| 0023   | [cosign verify gate — closing the supply-chain loop](0023-cosign-verify-and-disaster-recovery.md) | accepted  | 2026-12-01 |
| 0025   | [Deploy-time cosign verify — belt and suspenders](0025-deploy-verify-automation-cost.md) | accepted  | 2026-12-05 |
| 0028   | [Multi-provider Terraform — Hetzner + DigitalOcean](0028-multi-provider-and-architecture.md) | accepted  | 2026-12-09 |
| 0030   | [Maintenance window, recording rules, health CLI, capacity, audit](0030-operational-excellence.md) | accepted  | 2026-12-12 |
| 0031   | [v1.0.0 — stability declaration](0031-v1.0.0-stability-declaration.md) | accepted  | 2026-12-15 |
| 0032   | [Enforce Conventional Commits](0032-enforce-conventional-commits.md) | accepted  | 2026-12-16 |
| 0033   | [SLO, SLI, and error budget](0033-slo-sli-error-budget.md) | accepted  | 2026-12-18 |

## By theme

- **Deployment** — 0001, 0002, 0008, 0025
- **Backup and recovery** — 0003, 0006, 0007, 0012, 0023
- **Observability** — 0004, 0009, 0014, 0011, 0030, 0033
- **Security and supply chain** — 0005, 0013, 0016, 0017, 0019, 0020, 0023, 0025
- **Performance** — 0018
- **Infrastructure** — 0015, 0020, 0028
- **Process and stability** — 0031, 0032

## Writing a new ADR

1. Copy `0001-use-compose-as-the-deployment-unit.md` as a template.
2. Use the next free number (gaps are fine — see the note above).
3. Fill in Context, Decision, Rationale (with rejected alternatives),
   and Consequences.
4. Add a row to this index in the same PR.
5. Link the ADR from the relevant runbook or skill file.
