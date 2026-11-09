# Backup and restore runbook

## Nightly backup

A systemd timer (`deploy/systemd/stacksmith-backup.timer`) runs
`scripts/backup-db.sh` at 03:00 every night. The script:

1. Runs `pg_dump --clean --if-exists --no-owner --no-privileges` inside
   the postgres container, streams the output to the host, and gzips it
   into `backups/docubot-YYYYMMDD-HHMMSS.sql.gz`.
2. Writes a `.sha256` sidecar for integrity verification.
3. Prunes daily backups beyond the last 7 and weekly (Monday) backups
   beyond the last 4.

To install the timer on the host:

```bash
sudo cp deploy/systemd/stacksmith-backup.{timer,service} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now stacksmith-backup.timer
```

## Manual backup

```bash
bash scripts/backup-db.sh
```

## Restore

```bash
bash scripts/restore-db.sh backups/docubot-20261106-030000.sql.gz
```

The script:

1. Verifies the sha256 checksum if a `.sha256` sidecar exists.
2. Prompts for confirmation (type `RESTORE` to proceed). Use `--yes` to
   skip the prompt in automation.
3. Stops the app, worker and beat to prevent writes during restore.
4. Loads the dump with `gunzip | psql -v ON_ERROR_STOP=1`.
5. Restarts the app, worker and beat.

### What to check after restore

- `curl :8080/health/ready/` returns 200.
- `docker compose ps` shows all services healthy.
- Spot-check a known row in the database.

### When restore fails

- **Checksum mismatch.** The backup file is corrupt. Do not proceed; use
  the previous backup.
- **`psql` errors mid-restore.** The dump may be from a different schema
  version. Check the `ON_ERROR_STOP` output for the failing statement.
  If the schema drifted, restore the previous backup and investigate the
  migration that broke compatibility.

## The restore drill

The `restore-drill` workflow proves the restore path end to end:

1. Brings up the stack.
2. Seeds a `_drill_marker` row.
3. Takes a backup.
4. Drops the row.
5. Restores from the backup.
6. Verifies the row is back.

If this job is green, the backup is restorable. If it is red, the backup
strategy is broken and must be fixed before the next deploy.
