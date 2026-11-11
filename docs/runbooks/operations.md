# Operations runbook

This runbook covers the day-to-day and week-to-week operations for the
stacksmith deployment. For incident-specific steps, see
[failure-playbook.md](failure-playbook.md).

## Daily

### Morning check (2 minutes)

1. `curl :8080/health/ready/` — returns 200 with `"ready"`.
2. `docker compose -f docker-compose.prod.yml ps` — all services Up.
3. `ls -lh backups/` — a backup from last night exists and is non-empty.
4. `curl :9093/api/v2/alerts` — no firing alerts (or check the Alertmanager
   UI at `:9093`).
5. Open Grafana (`/grafana/`) — the services dashboard shows the health
   probe as UP.

If any of these fail, jump to the [failure playbook](failure-playbook.md).

### Deploy (when a new image is ready)

See [deploy.md](deploy.md). Summary:

```bash
bash scripts/deploy.sh        # blue → green (or vice versa)
# verify, then:
bash scripts/release.sh       # tag + manifest
```

## Weekly

### Backup drill (5 minutes)

The `restore-drill` workflow runs on every push, but a manual drill on the
host confirms the production backup (not just the CI one) is restorable:

1. `bash scripts/backup-db.sh` — take a fresh backup.
2. `bash scripts/restore-db.sh backups/docubot-<latest>.sql.gz --yes` —
   restore it to a throwaway database (or accept the overwrite on a
   staging host).
3. Verify a known row.

### Off-host sync check

1. `bash scripts/sync-backups.sh` — confirm the rsync to the off-host
   destination succeeds.
2. Log into the off-host and confirm the files are there.

### Dependency review

1. Review open Dependabot PRs.
2. Merge non-breaking bumps; test breaking bumps on a branch.

## Incident

When something is broken:

1. Open the [failure playbook](failure-playbook.md).
2. Find the symptom that matches.
3. Follow the numbered steps.

If no symptom matches:

1. `docker compose -f docker-compose.prod.yml logs --tail=200` — read the
   last 200 lines of every service.
2. `docker compose -f docker-compose.prod.yml ps` — check for restarting
   containers.
3. Open Grafana — check the dashboards for anomalies.
4. If the database is suspect, check `pg_isready` and the postgres logs
   specifically.

## Post-incident

After the incident is resolved:

1. Write a short postmortem: what happened, what broke, what fixed it,
   what to change to prevent it.
2. If a runbook step was missing or wrong, update this file.
3. If an alert did not fire when it should have, add it to
   `monitoring/alert_rules.yml`.
