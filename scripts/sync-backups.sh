#!/usr/bin/env bash
# sync-backups.sh — copy backups off-host over rsync with a lock file.
#
# Usage: bash scripts/sync-backups.sh [user@host:/path]
#
# The destination defaults to BACKUP_REMOTE from .env. A lock file prevents
# two concurrent runs from racing on the same destination.
set -euo pipefail

BACKUP_DIR="backups"
LOCK_FILE="${BACKUP_DIR}/.sync.lock"

DEST="${1:-${BACKUP_REMOTE:-}}"
if [ -z "$DEST" ]; then
  echo "[sync] no destination set — pass user@host:/path or set BACKUP_REMOTE in .env"
  exit 1
fi

# Acquire a lock so two cron runs do not race.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "[sync] another sync is already running ($LOCK_FILE held)"
  exit 0
fi

if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR"/docubot-*.sql.gz 2>/dev/null)" ]; then
  echo "[sync] no backups to copy"
  exit 0
fi

echo "[sync] copying $BACKUP_DIR/ to $DEST"
rsync -avz --delete \
  --include='docubot-*.sql.gz' \
  --include='docubot-*.sql.gz.sha256' \
  --exclude='*' \
  "$BACKUP_DIR/" "$DEST/"

echo "[sync] done"
