#!/usr/bin/env bash
# backup-db.sh — nightly pg_dump with compression, checksum and retention.
#
# Usage: bash scripts/backup-db.sh
#
# Produces: backups/docubot-YYYYMMDD-HHMMSS.sql.gz
#           backups/docubot-YYYYMMDD-HHMMSS.sql.gz.sha256
#
# Retention: keeps the last 7 daily backups and the last 4 weekly
# (Monday) backups. Older files are pruned.
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="backups"
DAILY_KEEP="${DAILY_KEEP:-7}"
WEEKLY_KEEP="${WEEKLY_KEEP:-4}"

mkdir -p "$BACKUP_DIR"

STAMP="$(date -u +%Y%m%d-%H%M%S)"
FILE="$BACKUP_DIR/docubot-${STAMP}.sql.gz"
SHA_FILE="${FILE}.sha256"

echo "[backup] dumping to $FILE"

# pg_dump inside the postgres container, stream out, gzip on the host.
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-docubot}" -d "${POSTGRES_DB:-docubot}" --clean --if-exists --no-owner --no-privileges \
  | gzip > "$FILE"

sha256sum "$FILE" > "$SHA_FILE"
echo "[backup] sha256: $(awk '{print $1}' "$SHA_FILE")"

# Retention: daily
echo "[backup] pruning daily backups (keep $DAILY_KEEP)"
# shellcheck disable=SC2012  # filenames are alphanumeric and timestamp-sorted
ls -1t "$BACKUP_DIR"/docubot-*.sql.gz 2>/dev/null | tail -n +"$((DAILY_KEEP + 1))" | while read -r old; do
  echo "[backup] removing $old"
  rm -f "$old" "${old}.sha256"
done

# Retention: weekly (Mondays). Keep the most recent WEEKLY_KEEP Monday backups.
echo "[backup] pruning weekly backups (keep $WEEKLY_KEEP)"
weekly_count=0
# shellcheck disable=SC2012  # filenames are alphanumeric and timestamp-sorted
ls -1t "$BACKUP_DIR"/docubot-*.sql.gz 2>/dev/null | while read -r f; do
  day=$(date -u -d "$(echo "$f" | grep -oE '[0-9]{8}' | head -1)" +%u 2>/dev/null || echo "")
  # day 1 = Monday
  if [ "$day" = "1" ]; then
    weekly_count=$((weekly_count + 1))
    if [ "$weekly_count" -gt "$WEEKLY_KEEP" ]; then
      echo "[backup] removing weekly $f"
      rm -f "$f" "${f}.sha256"
    fi
  fi
done

echo "[backup] done"
# shellcheck disable=SC2012  # informational listing only
ls -lh "$BACKUP_DIR"/docubot-*.sql.gz 2>/dev/null | tail -5
