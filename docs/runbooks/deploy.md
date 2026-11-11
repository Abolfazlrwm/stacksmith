# Deploy runbook

This runbook covers the normal deploy path and the rollback path for the
docubot stack. Both are single commands; this document explains what they
do and what to check when they fail.

## Prerequisites

- The stack is up (`make up`) and healthy (`curl :8080/health/ready/` returns 200).
- `.env` is present and passes `bash scripts/check-env.sh`.
- You are on the host that runs docker, as a user in the `docker` group.

## Normal deploy

```bash
bash scripts/deploy.sh
```

`deploy.sh` with no argument picks the inactive color (the one nginx is not
currently routing to). To force a specific color:

```bash
bash scripts/deploy.sh green
```

### What it does

1. Reads the active color from `nginx/upstreams.conf`.
2. Starts the inactive app instance (`app-blue` or `app-green`) with
   `docker compose up -d --wait --no-deps`. The `--wait` blocks until the
   new instance's healthcheck passes.
3. Rewrites `nginx/upstreams.conf` to point at the new color.
4. Reloads nginx (`nginx -s reload`) so it picks up the new upstream. nginx
   reload is graceful — in-flight requests finish on the old workers, new
   requests go to the new upstream.
5. Runs canary checks: `CANARY_PROBES` (default 5) probes at
   `CANARY_INTERVAL` (default 2s) intervals against `/health/live/` and
   `/health/ready/` through nginx. If any probe fails, the upstream is
   rolled back to the old color, nginx is reloaded, and the deploy exits
   non-zero. The new color is left running (no traffic) for log inspection.
6. Waits `GRACE_PERIOD` seconds (default 10) for in-flight requests to drain.
7. Stops the old app instance.

### What to check

- `curl :8080/health/live/` returns 200 with `"alive"`.
- `curl :8080/health/ready/` returns 200 with `"ready"`.
- `docker compose ps` shows the expected color running and the other stopped.
- `nginx/upstreams.conf` points at the expected color.

### When it fails

- **The new instance does not become healthy.** `deploy.sh` exits non-zero
  at step 2. The old instance is still running and still serving. The
  upstream has not been switched. Fix the image/config and re-run.
- **Canary checks fail.** `deploy.sh` rolls the upstream back to the old
  color and exits non-zero. The new color is still running (no traffic) —
  inspect its logs (`docker compose logs app-<color>`), fix the issue,
  stop the bad container (`docker compose stop app-<color>`), and re-run
  deploy.
- **nginx reload fails.** The new instance is up but nginx is still routing
  to the old one. Check `docker compose logs nginx`. The upstream file has
  been rewritten; you can either fix nginx and reload manually, or revert
  the upstream file and re-run deploy.
- **The old instance was stopped too early.** Increase `GRACE_PERIOD` and
  redeploy. There is no undo for in-flight requests that were dropped.

## Rollback

```bash
bash scripts/rollback.sh
```

`rollback.sh` reads the active color and deploys the other one — it is
`deploy.sh` with the opposite color. Use it when the new release is broken
and you need to return to the previous one immediately.

### What to check after rollback

- `curl :8080/health/live/` returns 200.
- `docker compose ps` shows the previous color running.
- `nginx/upstreams.conf` points at the previous color.
- The previous color's image is the one you expect (`docker image inspect
  stacksmith/app:latest`).

### When rollback is not enough

If the database schema changed irreversibly (a destructive migration),
rolling back the app does not roll back the database. In that case:

1. Roll back the app to the previous color.
2. Restore the database from the last backup (`bash scripts/restore-db.sh
   <file>`).
3. Investigate the migration before deploying again.

## Releases

```bash
bash scripts/release.sh
```

Creates an annotated git tag (`release-YYYYMMDD-HHMM`) and a manifest in
`releases/` recording the git sha, the app image digest and an env
fingerprint (the sha256 of the variable names, not their values). Use this
to correlate a deploy with a specific build.
