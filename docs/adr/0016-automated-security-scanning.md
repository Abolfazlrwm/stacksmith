# ADR-0016: Automated security scanning — CodeQL, Trivy, dependency review

- **Status:** accepted
- **Date:** 2026-11-21
- **Supersedes:** —

## Context

v0.3.0 ships a full deploy → monitor → backup → restore cycle with
encrypted backups, canary checks, Alertmanager, distributed tracing, and
secret rotation. But there is no automated vulnerability scanning:

- A new CVE in a Python dependency (Django, psycopg, redis, celery, OTel)
  is not detected until it breaks something.
- A vulnerability in a base image layer (python:3.12-slim, nginx:alpine,
  pgvector:pg17, redis:alpine) is not detected at all.
- A pull request that bumps a dependency to a vulnerable version is not
  blocked.

The operator has to manually check `pip-audit`, `trivy`, and
GitHub Dependabot alerts. This does not scale and is not honest — the
README claims "production-grade" without proving the supply chain is
clean.

## Decision

Add three CI workflows that scan every push and pull request:

1. **CodeQL** — GitHub's semantic code analysis. Runs on push, PR, and
   weekly on Monday. Analyzes the Python app code for injection, path
   traversal, and other code-level vulnerabilities. Results upload to the
   GitHub Security tab.

2. **Trivy container scan** — builds the `stacksmith/app:latest` image
   and scans it for known CVEs at CRITICAL and HIGH severity. Fails the
   build if an unfixed vulnerability is found (`--ignore-unfixed` so we
   only fail on fixable issues). Results upload as SARIF to the Security
   tab and as a build artifact.

3. **Dependency review** — on every PR to `main`, checks changed
   dependencies for known vulnerabilities and license issues. Fails on
   MODERATE or above. Comments a summary in the PR if it fails.

## Rationale

- **Three layers, three tools.** CodeQL catches code vulnerabilities
  (SQL injection, XSS). Trivy catches image-layer vulnerabilities (OS
  packages, Python packages in the image). Dependency review catches
  vulnerable dependency bumps before they merge. Together they cover the
  three real supply-chain attack surfaces.
- **SARIF to the Security tab.** Both CodeQL and Trivy upload SARIF
  results, so vulnerabilities appear in one place (the GitHub Security
  tab) with deduplication and alert management.
- **`--ignore-unfixed` for Trivy.** Failing on every CVE — including
  those with no available fix — would make CI permanently red and train
  the operator to ignore it. We fail only on vulnerabilities that have a
  fix available.
- **`fail-on-severity: moderate` for dependency review.** LOW
  vulnerabilities are informational; MODERATE and above are blockers.
  This matches the severity routing in Alertmanager (ADR-0011).
- **Weekly CodeQL schedule.** New CodeQL rules are published regularly;
   a weekly run catches issues that were not detectable when the code was
   written.

## Considered alternatives

### pip-audit in CI

Not rejected, but not added separately. Trivy scans the built image
which includes all Python packages — it catches the same vulnerabilities
pip-audit would, plus OS-level packages. Adding pip-audit would be
redundant. If we ever need to scan requirements.txt before building the
image (e.g. in a pre-merge check that does not build), pip-audit is the
right tool for that specific job.

### Snyk

Rejected. Snyk is excellent but requires an API key and a Snyk account.
The free tier has limits; the paid tier is not justified for a
portfolio repo. Trivy is free, open-source, and runs locally.

### GitHub Dependabot security updates

Already enabled (`.github/dependabot.yml` from Phase 0). Dependabot
opens PRs when a dependency has a known vulnerability; the dependency
review workflow is the gate that prevents merging a PR that introduces
a new one. They complement each other.

### Grype instead of Trivy

Not rejected, but Trivy is more widely used and has better SARIF
support. Grype is a fine alternative; the choice is not load-bearing.

## Consequences

- Three new workflows: `codeql.yml`, `container-scan.yml`,
  `dependency-review.yml`.
- CodeQL runs weekly on Monday (in addition to push/PR).
- Trivy scans the built image; the build step reuses the prod compose's
  `app-blue` build, so the scanned image is the one that ships.
- The GitHub Security tab shows CodeQL and Trivy alerts. Dependabot
  alerts appear there too.
- `SECURITY.md` is updated with the scanning section and the v0.3.0
  posture (encrypted backups, automated TLS, Grafana behind nginx).
- A CRITICAL or HIGH unfixed CVE in the app image will block CI until
  the dependency is bumped or the vulnerability is triaged.
