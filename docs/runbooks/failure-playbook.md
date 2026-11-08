# Failure playbook

Symptom-first runbook for the failures that actually happen. Each section
is numbered steps, not prose.

## Disk full

Symptom: `HostDiskFull` alert fires; `docker compose ps` shows containers
restarting; writes fail.

1. `df -h` — confirm which filesystem is full.
2. `docker system df` — check docker disk usage (images, containers,
   volumes).
3. `docker compose -f docker-compose.prod.yml logs --tail=50 postgres` —
   check if postgres stopped accepting writes.
4. If docker images are the culprit:
   `docker image prune -a --filter "until=48h"` — remove unused images
   older than 48 hours.
5. If the pgdata volume is the culprit:
   - `bash scripts/backup-db.sh` — take a backup.
   - `docker compose -f docker-compose.prod.yml exec postgres vacuumdb
     --all --full` — reclaim space from dead tuples.
6. If backups are the culprit:
   `ls -lh backups/` — check the retention pruned correctly. If not, prune
   manually.
7. After freeing space: `docker compose -f docker-compose.prod.yml up -d`
   to restart any stopped containers.

## Worker OOM

Symptom: `ContainerRestartStorm` alert fires on the worker; `docker compose
logs worker` shows `Killed` or MemoryError.

1. `docker compose -f docker-compose.prod.yml logs --tail=100 worker` —
   confirm the OOM.
2. `docker stats` — watch the worker's memory.
3. Reduce concurrency: edit `.env`, set `CELERY_WORKER_CONCURRENCY=1` (or
   add `--concurrency 1` to the worker command).
4. `docker compose -f docker-compose.prod.yml up -d --no-deps worker` —
   restart with the new setting.
5. If the task itself leaks, identify it from the logs and fix the task.
   The worker restart is a bandage, not a fix.
6. If the host does not have enough RAM, either reduce
   `GUNICORN_WORKERS` or move to a larger VPS.

## Certificate expiry

Symptom: browsers show a TLS warning; `curl https://...` fails with a cert
error.

The stack currently terminates TLS at nginx with a template config (see
`nginx/default.conf`). To enable real TLS:

1. Obtain a cert (e.g. with certbot / Let's Encrypt).
2. Place `fullchain.pem` and `privkey.pem` in `nginx/certs/`.
3. Uncomment the `:443` server block in `nginx/default.conf`.
4. `docker compose -f docker-compose.prod.yml exec nginx nginx -s reload`.
5. Set a calendar reminder 30 days before expiry. certbot's
   `--deploy-hook` can automate the reload, but the expiry check is manual
   until a renewal pipeline is added.

## Postgres failure

Symptom: `AppHealthProbeFailing` fires; `/health/ready/` returns 503 with
`postgres: fail`; app logs show connection refused.

1. `docker compose -f docker-compose.prod.yml ps postgres` — is it
   running?
2. `docker compose -f docker-compose.prod.yml logs --tail=100 postgres` —
   read the error.
3. If postgres is stopped:
   `docker compose -f docker-compose.prod.yml up -d postgres` — restart.
4. If postgres won't start (corrupt WAL, bad config):
   - `bash scripts/restore-db.sh backups/docubot-<latest>.sql.gz --yes` —
     restore from the last good backup.
   - This is the scenario the restore drill exists for.
5. If the pgdata volume is corrupt and the restore fails:
   - Stop the stack: `docker compose down`.
   - Remove the volume: `docker volume rm stacksmith_pgdata`.
   - Bring up the stack: `docker compose up -d --wait`.
   - Restore from backup: `bash scripts/restore-db.sh <file> --yes`.
6. Post-incident: write a postmortem. Why did postgres fail? Was it disk,
   memory, or a bad migration?

## Nginx failure

Symptom: all requests return 502; `docker compose ps nginx` shows it
restarting.

1. `docker compose -f docker-compose.prod.yml logs --tail=50 nginx` — read
   the error.
2. Common cause: the upstream in `nginx/upstreams.conf` points at a color
   that is not running.
   - `cat nginx/upstreams.conf` — which color is active?
   - `docker compose ps` — is that color running?
   - If not: `bash scripts/deploy.sh <color>` — start it.
3. Common cause: a syntax error in `nginx/default.conf` after a manual
   edit.
   - `docker compose -f docker-compose.prod.yml exec nginx nginx -t` —
     test the config.
   - Fix the config and reload.
