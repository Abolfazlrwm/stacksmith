# ADR-0025: Deploy-time cosign verify — belt and suspenders

- **Status:** accepted
- **Date:** 2026-12-05
- **Supersedes:** the "deploy-time cosign verify is on the v0.7 roadmap" item from known-limitations

## Context

ADR-0023 ships a CI verify gate that checks the cosign signature after
the image is built and signed. But `deploy.sh` does not verify the
signature before switching the upstream. An operator who pulls a
malicious image (e.g. from a compromised registry token) and deploys it
gets no warning at deploy time.

## Decision

Add a step 0 to `deploy.sh` that calls `cosign verify` before starting
the target app instance. If the image is from GHCR and cosign is
installed, the signature is verified. If verification fails, the deploy
aborts before any traffic is switched.

## Rationale

- **CI verify is the gate; deploy verify is the lock.** CI verify proves
  the image was signed when it was pushed. Deploy verify proves the image
  is still signed when it is deployed. A registry compromise between CI
  and deploy is caught by the deploy-time check.
- **Graceful degradation.** If cosign is not installed or the image is a
  local build (not from GHCR), the verify is skipped with a message. The
  operator can install cosign on the VPS to enable the check.
- **Hard abort.** If cosign verify fails, `deploy.sh` exits non-zero
  before starting the target instance. No traffic is switched.

## Consequences

- `deploy.sh` checks for `cosign` in PATH and `$APP_IMAGE` containing
  `ghcr.io`. If both are true, it verifies the signature.
- The verify uses the same identity regex as the CI verify.
- If the image is local (`stacksmith/app:latest`) or cosign is not
  installed, the deploy proceeds without verification.
- The operator should install cosign on the VPS: `apt install cosign`
  or `brew install cosign`.

---

# ADR-0026: Release drafter and Dependabot auto-merge

- **Status:** accepted
- **Date:** 2026-12-06
- **Supersedes**: —

## Context

Releases are currently drafted manually from the CHANGELOG. Dependabot
PRs (for Docker base image and GitHub Actions bumps) require manual
review and merge even for trivial patch bumps.

## Decision

1. **Release drafter** — a workflow that maintains a draft GitHub Release
   from PR titles and labels. When a tag is pushed, the draft becomes the
   release notes. Configured in `.github/release-drafter.yml` with
   categories matching the conventional commit prefixes.

2. **Dependabot auto-merge** — a workflow that auto-approves and
   auto-merges patch and minor dependency bumps after CI passes. Major
   bumps are labeled `needs-review` and left for manual review.

## Rationale

- **Release drafter saves 30 minutes per release.** The draft is
  maintained incrementally as PRs merge, so the release notes are always
  up to date. The operator just publishes the draft when ready.

- **Auto-merge for patch and minor is safe.** Dependabot patch bumps
  (e.g. `1.2.3` → `1.2.4`) are backward-compatible by definition. Minor
  bumps (e.g. `1.2.3` → `1.3.0`) add features but should not break. CI
  (lint, smoke, all drills) gates the merge — if a bump breaks anything,
  CI is red and the auto-merge does not fire (`--auto` waits for checks).

- **Major bumps need a human.** A major bump (e.g. `1.2.3` → `2.0.0`)
  can break the app. The workflow labels it `needs-review` and comments
  a warning. The operator reviews breaking changes before merging.

## Consequences

- `release-drafter.yml` runs on push to main and on PR events.
- `dependabot-auto-merge.yml` runs on `pull_request_target` from
  `dependabot[bot]`.
- Patch and minor bumps merge automatically after CI passes.
- Major bumps are labeled and commented, not merged.
- The release draft is always available on the GitHub Releases page.

---

# ADR-0027: Cost monitoring dashboard

- **Status:** accepted
- **Date:** 2026-12-07
- **Supersedes**: —

## Context

The kit ships monitoring for availability, performance, and security.
What is missing is **cost visibility**: how much does this VPS actually
cost, and which service consumes the most resources?

## Decision

Add a cost monitoring dashboard (`grafana/dashboards/cost.json`) and a
`scripts/cost-metric.sh` that writes a textfile metric with the monthly
VPS cost estimate and cost-per-CPU-hour. The dashboard shows:

- Monthly cost estimate (from `COST_VPS_MONTHLY_USD`, default $8)
- CPU usage % (avg across containers)
- Memory usage %
- Network I/O
- Disk usage per mountpoint
- Cost breakdown by service (CPU-weighted)

## Rationale

- **Cost is a first-class metric.** A deployment kit that monitors
  availability but not cost is half a kit. The operator should know at a
  glance whether they are overpaying for idle resources.

- **Textfile metric, not a new exporter.** The cost is a static value
  (the VPS plan price), not a live measurement. A textfile metric written
  by `cost-metric.sh` (cron or systemd timer) is the right transport —
  same as the backup freshness metric (ADR-0006).

- **CPU-weighted breakdown.** The cost-per-service panel multiplies each
  container's CPU usage by the cost-per-CPU-hour. This gives a rough
  "which service is expensive" view without per-container billing.

## Consequences

- `scripts/cost-metric.sh` writes `monitoring/textfile/cost.prom` with
  two gauges: `stacksmith_cost_estimate_usd` and
  `stacksmith_cost_per_cpu_hour`.
- The operator runs it via cron or systemd timer (same pattern as
  `backup-db.sh`).
- `grafana/dashboards/cost.json` is a provisioned Grafana dashboard.
- The cost estimate is a constant (the VPS plan price), not a live
  measurement. For live cloud billing, the operator would use the cloud
  provider's billing API — out of scope for this kit.
