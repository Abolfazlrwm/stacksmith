# Security Policy

## Supported Versions

StackSmith is at `v0.1.0`. Security fixes land on the **latest release line**;
there is no long-term-support branch yet.

| Version | Supported |
|---------|-----------|
| 0.1.x (latest) | yes |
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

## Security posture of this kit

Stated plainly, including the weak spots:

- **Secrets live in `.env` on the host** (gitignored, documented in
  `.env.example`), not in a secret manager. ADR-0005 records this decision
  and the rotation procedure. Protect the host accordingly: `chmod 600`,
  no shared shells, no secrets in logs.
- **No secret ever lands in git, logs or release manifests.** Manifests
  fingerprint the environment by variable names only, never by values.
- **Backups are checksummed (sha256) before they leave the host.** They are
  not encrypted at rest yet — off-host encryption with `age` is planned for
  v0.2. Until then, protect the backup destination like the database itself.
- **The restore path requires a checksum match and an explicit confirmation**
  (`--yes` for CI), so a corrupted or truncated dump cannot silently wipe the
  database.
- **TLS is a template, not automated** — see `docs/known-limitations.md`.
  Until real certificates are in place, do not point this stack at the
  public internet.
- **Grafana listens on port 3000 directly**, not behind nginx with auth.
  Restrict it with a firewall on a public host.
- **Single host.** There is no HA and no multi-tenant isolation story here;
  the kit assumes you control the whole machine.
