# ADR-0013: Secret rotation with zero downtime

- **Status:** accepted
- **Date:** 2026-11-18
- **Supersedes:** the "No automated secret rotation" item in known-limitations

## Context

ADR-0005 documented secret rotation as a manual procedure: generate a key,
edit `.env`, deploy, restart services. The v0.3 roadmap (issue #20) lists
"Secret rotation automation" as the third item.

## Decision

`scripts/rotate-secrets.sh` automates the rotation of
`DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD`. Both rotations are
zero-downtime:

- **DJANGO_SECRET_KEY** — generate a new key, write to `.env`, then
  deploy with `deploy.sh`. The blue-green deploy means both colors run
  briefly; the new color has the new key, the old color has the old key
  until it is stopped. Existing sessions are invalidated (users are
  logged out); no data is lost.

- **POSTGRES_PASSWORD** — take a safety backup, `ALTER USER` in postgres,
  write the new password to `.env`, `--force-recreate` the app, worker and
  beat. They reconnect with the new password. The `ALTER USER` takes
  effect immediately; existing connections are not dropped, so the app
  keeps serving until it reconnects.

## Rationale

- **A safety backup before touching the password.** If `ALTER USER`
  fails mid-way (unlikely but possible), the database is unchanged and
  the backup is the fallback.
- **`--force-recreate` for the password, `deploy.sh` for the key.** The
  key rotation needs a blue-green deploy because Django validates the key
  on startup — a `--force-recreate` would briefly stop the app. The
  password rotation can `--force-recreate` because postgres accepts both
  old and new passwords until all connections reconnect (the old password
  stops working the moment `ALTER USER` commits, but existing sessions
  are not dropped).
- **The script does not restart postgres.** `ALTER USER` does not require
  a restart. Restarting postgres would drop all connections and cause
  downtime.
- **Tested end to end.** The `rotation-drill` workflow rotates both
  secrets and verifies `/health/live/` and `/health/ready/` at every
  step.

## Considered alternatives

### HashiCorp Vault dynamic secrets

Rejected (ADR-0005 already rejected Vault for this scale). The rotation
script does what Vault would do, without the Vault dependency.

### Kubernetes Secrets with rotation controllers

Rejected with Kubernetes (ADR-0001).

### Manual rotation only (v0.2.0 behavior)

Rejected for v0.3. The manual procedure worked but was never tested.
The drill proves the rotation path works; the script makes it
repeatable.

## Consequences

- `scripts/rotate-secrets.sh` rotates both secrets by default; `--key`
  and `--password` flags rotate individually.
- The key rotation requires a subsequent `deploy.sh` (the script prints a
  reminder). The password rotation restarts the app immediately.
- The `rotation-drill` CI workflow rotates both secrets and verifies the
  stack stays healthy throughout.
- The operator should run this on a schedule (e.g. quarterly) via cron or
  a calendar reminder. The script itself does not schedule.
- This decision closes the "Secret rotation automation" item from the
  v0.3 roadmap (issue #20).
