#!/usr/bin/env bash
# backup-db.sh — nightly pg_dump with compression, checksum, retention and metric.
#
# Usage: bash scripts/backup-db.sh
#
# Produces: backups/docubot-YYYYMMDD-HHMMSS.sql.gz
#           backups/docubot-YYYYMMDD-HHMMSS.sql.gz.sha256
#           monitoring/textfile/backup.prom   (node-exporter textfile metric)
#
# Retention: keeps the last 7 daily backups and the last 4 weekly
# (Monday) backups. Older files are pruned.
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="backups"
TEXTFILE_DIR="monitoring/textfile"
METRIC_FILE="$TEXTFILE_DIR/backup.prom"
DAILY_KEEP="${DAILY_KEEP:-7}"
WEEKLY_KEEP="${WEEKLY_KEEP:-4}"

mkdir -p "$BACKUP_DIR" "$TEXTFILE_DIR"

STAMP="$(date -u +%Y%m%d-%H%M%S)"
EPOCH="$(date -u +%s)"
FILE="$BACKUP_DIR/docubot-${STAMP}.sql.gz"
SHA_FILE="${FILE}.sha256"

echo "[backup] dumping to $FILE"

# pg_dump inside the postgres container, stream out, gzip on the host.
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-docubot}" -d "${POSTGRES_DB:-docubot}" --clean --if-exists --no-owner --no-privileges \
  | gzip > "$FILE"

SIZE="$(stat -c %s "$FILE")"

sha256sum "$FILE" > "$SHA_FILE"
echo "[backup] sha256: $(awk '{print $1}' "$SHA_FILE")"

# Write the textfile metric so node-exporter exposes backup freshness.
# The BackupStale alert (monitoring/alert_rules.yml) fires when
# time() - backup_last_success_timestamp_seconds > 93600 (26h).
write_metric() {
  local status="$1"
  local tmp="$METRIC_FILE.$$"
  {
    echo "# HELP backup_last_success_timestamp_seconds Unix timestamp of the last successful backup."
    echo "# TYPE backup_last_success_timestamp_seconds gauge"
    if [ "$status" = "ok" ]; then
      echo "backup_last_success_timestamp_seconds $EPOCH"
    else
      echo "backup_last_success_timestamp_seconds 0"
    fi
    echo "# HELP backup_last_success_bytes Size of the last backup in bytes."
    echo "# TYPE backup_last_success_bytes gauge"
    if [ "$status" = "ok" ]; then
      echo "backup_last_success_bytes $SIZE"
    else
      echo "backup_last_success_bytes 0"
    fi
    echo "# HELP backup_last_status 1 if the last backup succeeded, 0 otherwise."
    echo "# TYPE backup_last_status gauge"
    if [ "$status" = "ok" ]; then
      echo "backup_last_status 1"
    else
      echo "backup_last_status 0"
    fi
  } > "$tmp"
  mv "$tmp" "$METRIC_FILE"
  echo "[backup] metric written to $METRIC_FILE"
}

write_metric ok

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
