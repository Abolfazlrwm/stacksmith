# Security Policy

## Supported Versions

StackSmith is at `v1.2.2`. Security fixes land on the **latest release line**;
there is no long-term-support branch yet.

| Version | Supported |
|---------|-----------|
| 1.2.x (latest) | yes |
| 1.1.x | no |
| 1.0.x | no |
| 0.x | no |

## Reporting a Vulnerability

Please **do not open a public issue** for a security problem.

Report it privately through
[GitHub Private Vulnerability Reporting](https://github.com/Abolfazlrwm/stacksmith/security/advisories/new)
on this repository. That channel keeps the report visible only to the
maintainer until it is ready to disclose.

**What to expect:**

- Acknowledgement within 48 hours of the report.
- An initial assessment and a remediation timeline within 7 days.
- A fix or a documented mitigation within 30 days for a confirmed
  high-severity issue (severity assessed against the CVSS v3.1 rubric
  and the scope below).
- Credit in the advisory and the release notes, unless you prefer to stay
  anonymous.

**What helps:**

- A minimal reproducer (a `curl` command, a `docker compose` snippet,
  a single Python file) is worth a thousand words.
- If you have a fix in mind, include it as a patch — it speeds the
  review and lets me credit you as a co-author of the advisory.
- If you are a security researcher and need a CVE, say so up front; I
  will request one through GitHub's CVE flagging when the advisory is
  ready to publish.

## Scope

In scope — anything in this repository that could let an attacker reach
the host, the database, the document corpus, the backups, or the
LLM-cost budget:

- The Django application (`app/`) — the docubot product surface:
  document upload, RAG retrieval, the chat endpoint, the health
  endpoints, the admin, the security middleware, the rate limiter.
- The compose files (`docker-compose*.yml`) and the nginx configuration.
- The operational scripts (`scripts/`) — deploy, rollback, backup,
  restore, rotation, drill runners.
- The CI workflows (`.github/workflows/`).
- The OpenTelemetry instrumentation (`app/config/telemetry.py`).

Out of scope — vulnerabilities that exist only in third-party
dependencies (report them upstream; Dependabot surfaces them here) and
vulnerabilities that require a compromise of the single host the kit
runs on (the kit assumes you control the whole machine — ADR-0015
documents what multi-host isolation would require).

## Automated security scanning

Five CI workflows scan every push and pull request:

- **CodeQL** (`.github/workflows/codeql.yml`) — semantic analysis of the
  Python app code. Runs on push, PR, and weekly on Monday. Results upload
  to GitHub Security tab.
- **Trivy container scan** (`.github/workflows/container-scan.yml`) —
  scans the built `stacksmith/app:latest` image for known CVEs at CRITICAL
  and HIGH severity. Fails the build if an unfixed vulnerability is found.
  Results upload as SARIF to the Security tab.
- **Trivy filesystem scan** (`.github/workflows/container-scan.yml`) —
  scans the repo itself for misconfigurations and secrets before the
  image is built.
- **Dependency review** (`.github/workflows/dependency-review.yml`) — on
  every PR to `main`, checks changed dependencies for known
  vulnerabilities and license issues. Fails on MODERATE or above.
- **Dependabot** (`.github/dependabot.yml`) — opens PRs for outdated
  dependencies across pip (`app/requirements.txt`), npm
  (`commitlint/`), Docker base images, and GitHub Actions. Runs weekly.

## Security posture

Stated plainly, including the weak spots — so a reporter can check the
likely-affected component before filing:

### Secrets and backups

- **Secrets live in `.env` on the host** (gitignored, documented in
  `.env.example`), not in a secret manager. ADR-0005 records this
  decision and the rotation procedure. `scripts/rotate-secrets.sh`
  automates zero-downtime rotation (ADR-0013).
- **No secret ever lands in git, logs or release manifests.** Manifests
  fingerprint the environment by variable names only, never by values.
- **Backups are checksummed (sha256) and encrypted with `age` before
  they leave the host** (ADR-0007). The private key never touches the
  VPS; a compromised host cannot decrypt its own backups.
- **The restore path requires a checksum match and an explicit
  confirmation** (`--yes` for CI), so a corrupted or truncated dump
  cannot silently wipe the database. Backup integrity is verified
  against a throwaway database (ADR-0012).

### App boundary (v1.2.2 hardening — ADR-0037)

- **`ALLOWED_HOSTS` fails closed** to a list of the canonical hostname
  plus loopback addresses; a misconfigured prod deploy answers 400
  instead of the requested host. Operators override via
  `DJANGO_ALLOWED_HOSTS`.
- **`SECURE_*` headers** (HSTS, content-type nosniff, referrer policy,
  X-Frame-Options) are set at the app layer, not just the proxy, so
  the canary probe and direct port-8000 access see hardened responses.
- **`SECURE_SSL_REDIRECT` is opt-in, default off** — turning it on by
  default broke every container drill (the in-container readiness probe
  sees 301 forever and the stack never reports healthy). `/health/*`
  is exempt as belt-and-suspenders.
- **Upload validation** (`documents.ingestion.validate_upload`) runs
  three layers of defense before any bytes reach disk: extension
  allow-list (`{.pdf, .md, .markdown, .txt, .text}`), magic-byte sniff
  for PDF (`%PDF-`), and a UTF-8 decode check for text kinds. A renamed
  EXE-as-`evil.pdf` is rejected at the door.
- **Path-traversal rejection** in the upload view: filenames with `/`
  or `\` are refused with a 400; storage is keyed by checksum but the
  name is echoed in the response, so it must be a bare filename.
- **Filename length capped at 255 chars** before any disk I/O.

### Rate limiting (v1.2.3 — ADR-0038)

- **`/api/chat/` is rate-limited at 60/min per owner** (X-Docubot-Owner
  header set by the reverse proxy; falls back to client IP). The
  endpoint calls an external LLM per request, so a runaway loop or a
  careless script is a cost cascade, not just a load spike. A 429
  carries `Retry-After` and `X-RateLimit-*` headers so clients can
  self-throttle. Health probes and admin are exempt.
- **The limiter fails OPEN** if Redis is unreachable — the readiness
  probe catches Redis-down independently, and the limiter must not
  become a new single point of failure.

### TLS, network, monitoring

- **TLS is automated** — certbot runs in a renewal loop (ADR-0010) and
  reloads nginx after each successful renewal.
- **Grafana is behind nginx with basic auth**. Port 3000 is not
  exposed directly.
- **Alerts route to Slack** via Alertmanager (ADR-0011). A failed
  backup pages within 5 minutes; a stale backup pages within 26 hours.
- **Single host.** There is no HA and no multi-tenant isolation story
  here; the kit assumes you control the whole machine. ADR-0015
  documents what multi-host would require.

### Known weak spots

- **The chat API is anonymous.** Auth is delegated to the reverse
  proxy (nginx sets `X-Docubot-Owner` after its own auth). A
  misconfigured proxy that drops the header, or a leaked header, lets
  an unauthenticated client reach the LLM. The rate limiter (ADR-0038)
  caps the blast radius; a future phase can swap in a real session/JWT
  without changing the view code.
- **`DOCUBOT_UPLOAD_ROOT` is on a local volume**, not an object store.
  A host compromise can read every uploaded document. The backup
  encryption (ADR-0007) protects the off-host copy, not the live volume.
- **No CSP.** The chat UI is a single-page HTML file with inline
  scripts. A future phase can add a strict CSP once the UI is split
  into separate static assets.

## Disclosure policy

- A confirmed vulnerability is fixed on a private branch, then released
  in a patch version (e.g. `v1.2.3` for a fix on the `1.2` line) with a
  `CHANGELOG` entry and an ADR.
- The GitHub Security Advisory is published at the same time as the
  release, with credit to the reporter unless they request anonymity.
- We do not embargo fixes beyond the time needed to verify the fix
  and run the drill suite (typically a few days for a high-severity
  issue).
