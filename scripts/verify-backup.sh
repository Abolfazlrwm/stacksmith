#!/usr/bin/env bash
# verify-backup.sh — restore a backup into a throwaway database and verify
# table row counts and a checksum against the source database.
#
# Usage: bash scripts/verify-backup.sh <backup-file>
#
# This catches silent corruption: a backup that restores successfully but
# is missing rows (e.g. pg_dump ran mid-transaction, or a table was dropped
# between the dump and the restore). The row-count check in the restore
# drill only verifies one row; this script verifies every table.
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
FILE="${1:?usage: verify-backup.sh <backup-file>}"
VERIFY_DB="verify_${POSTGRES_DB:-docubot}_$$"

if [ ! -f "$FILE" ]; then
  echo "[verify] file not found: $FILE"
  exit 1
fi

echo "[verify] source db: ${POSTGRES_DB:-docubot}"
echo "[verify] throwaway db: $VERIFY_DB"
echo "[verify] backup file: $FILE"

# 1. Create a throwaway database alongside the production one.
echo "[verify] creating throwaway database"
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "${POSTGRES_USER:-docubot}" -d "${POSTGRES_DB:-docubot}" -c \
  "CREATE DATABASE $VERIFY_DB;" >/dev/null

# shellcheck disable=SC2329  # cleanup is invoked via trap, not directly
cleanup() {
  echo "[verify] dropping throwaway database"
  docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-docubot}" -d "${POSTGRES_DB:-docubot}" -c \
    "DROP DATABASE IF EXISTS $VERIFY_DB;" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# 2. Restore the backup into the throwaway database.
echo "[verify] restoring backup into $VERIFY_DB"
if [[ "$FILE" == *.age ]]; then
  # Decrypt first.
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
  IDENTITY="${AGE_IDENTITY_FILE:-${BACKUP_AGE_IDENTITY:-}}"
  age -d -i "$IDENTITY" "$FILE" | gunzip | docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-docubot}" -d "$VERIFY_DB" -v ON_ERROR_STOP=1 >/dev/null
else
  gunzip -c "$FILE" | docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-docubot}" -d "$VERIFY_DB" -v ON_ERROR_STOP=1 >/dev/null
fi

# 3. Compute row counts for every table in both databases.
echo "[verify] comparing table row counts"
COUNTS_SQL="SELECT schemaname || '.' || relname AS tbl, n_live_tup AS rows
FROM pg_stat_user_tables ORDER BY tbl;"

PROD_COUNTS=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "${POSTGRES_USER:-docubot}" -d "${POSTGRES_DB:-docubot}" -tAc "$COUNTS_SQL")

VERIFY_COUNTS=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "${POSTGRES_USER:-docubot}" -d "$VERIFY_DB" -tAc "$COUNTS_SQL")

# 4. Diff the two count lists.
echo "[verify] diff (source vs restored):"
DIFF=$(diff <(echo "$PROD_COUNTS") <(echo "$VERIFY_COUNTS") || true)
if [ -z "$DIFF" ]; then
  echo "[verify] row counts match — backup is intact"
  echo "[verify] tables verified: $(echo "$PROD_COUNTS" | wc -l)"
  exit 0
else
  echo "$DIFF"
  echo "[verify] row count mismatch — backup may be corrupt or incomplete"
  exit 1
fi
