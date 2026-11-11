# Security Policy

## Supported Versions

StackSmith is at `v0.3.0`. Security fixes land on the **latest release line**;
there is no long-term-support branch yet.

| Version | Supported |
|---------|-----------|
| 0.3.x (latest) | yes |
| older lines | no |

## Reporting a Vulnerability

Please **do not open a public issue** for a security problem.

Report it privately through
[GitHub Private Vulnerability Reporting](https://github.com/Abolfazlrwm/stacksmith/security/advisories/new)
on this repository. That channel keeps the report visible only to the
maintainer until it is ready to disclose.

**What to expect:**

- Acknowledgement within 48 hours of the report.
- An initial assessment and a remediation timeline within 7 days.
- Credit in the advisory and the release notes, unless you prefer to stay
  anonymous.

## Scope

StackSmith is a deployment kit. In scope: the compose files, the nginx
configuration, the operational scripts (`scripts/`), and the CI workflows —
anything that could let an attacker reach the host, the database, or the
backups through this kit.

Out of scope: vulnerabilities in the docubot application itself. That is a
different codebase with its own
[security process](https://github.com/Abolfazlrwm/docubot/security/policy) —
report those there.

## Automated security scanning

Three CI workflows scan every push and pull request:

- **CodeQL** (`.github/workflows/codeql.yml`) — semantic analysis of the
  Python app code. Runs on push, PR, and weekly on Monday. Results upload
  to GitHub Security tab.
- **Trivy container scan** (`.github/workflows/container-scan.yml`) —
  scans the built `stacksmith/app:latest` image for known CVEs at CRITICAL
  and HIGH severity. Fails the build if an unfixed vulnerability is found.
  Results upload as SARIF to the Security tab.
- **Dependency review** (`.github/workflows/dependency-review.yml`) — on
  every PR to `main`, checks changed dependencies for known vulnerabilities
  and license issues. Fails on MODERATE or above.

## Security posture of this kit

Stated plainly, including the weak spots:

- **Secrets live in `.env` on the host** (gitignored, documented in
  `.env.example`), not in a secret manager. ADR-0005 records this decision
  and the rotation procedure. `scripts/rotate-secrets.sh` automates
  zero-downtime rotation (ADR-0013).
- **No secret ever lands in git, logs or release manifests.** Manifests
  fingerprint the environment by variable names only, never by values.
- **Backups are checksummed (sha256) and encrypted with `age` before they
  leave the host** (ADR-0007). The private key never touches the VPS; a
  compromised host cannot decrypt its own backups.
- **The restore path requires a checksum match and an explicit confirmation**
  (`--yes` for CI), so a corrupted or truncated dump cannot silently wipe the
  database. Backup integrity is verified against a throwaway database
  (ADR-0012).
- **TLS is automated** — certbot runs in a renewal loop (ADR-0010) and
  reloads nginx after each successful renewal.
- **Grafana is behind nginx with basic auth** (ADR in the Phase 6.6 PR).
  Port 3000 is not exposed directly.
- **Alerts route to Slack** via Alertmanager (ADR-0011). A failed backup
  pages within 5 minutes; a stale backup pages within 26 hours.
- **Single host.** There is no HA and no multi-tenant isolation story here;
  the kit assumes you control the whole machine. ADR-0015 documents what
  multi-host would require.
