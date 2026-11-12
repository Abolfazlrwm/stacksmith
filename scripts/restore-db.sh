#!/usr/bin/env bash
# restore-db.sh — restore the database from a backup file with a pre-flight check.
#
# Usage: bash scripts/restore-db.sh <file> [--yes]
#
# Accepts:
#   - docubot-*.sql.gz          (plaintext local backup)
#   - docubot-*.sql.gz.age      (encrypted off-host backup; decrypts first)
#
# The --yes flag skips the interactive confirmation (for CI / automation).
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
FILE="${1:?usage: restore-db.sh <file> [--yes]}"
CONFIRM="${2:-}"

if [ ! -f "$FILE" ]; then
  echo "[restore] file not found: $FILE"
  exit 1
fi

# If the file is encrypted (.age), decrypt it first to a temp file and
# run the rest of the pipeline against the decrypted .gz.
DECRYPTED_TMP=""
if [[ "$FILE" == *.age ]]; then
  echo "[restore] file is encrypted; decrypting first"
  DECRYPTED_TMP="$(mktemp -t docubot-restore.XXXXXX.sql.gz)"
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
  IDENTITY="${AGE_IDENTITY_FILE:-${BACKUP_AGE_IDENTITY:-}}"
  if [ -z "$IDENTITY" ] || [ ! -f "$IDENTITY" ]; then
    echo "[restore] age identity not found — set BACKUP_AGE_IDENTITY in .env"
    rm -f "$DECRYPTED_TMP"
    exit 1
  fi
  age -d -i "$IDENTITY" -o "$DECRYPTED_TMP" "$FILE"
  GZ_FILE="$DECRYPTED_TMP"
  trap 'rm -f "$DECRYPTED_TMP"' EXIT
  echo "[restore] decrypted to $GZ_FILE"
else
  GZ_FILE="$FILE"
fi

# Pre-flight: verify the sha256 checksum if a .sha256 sidecar exists.
SHA_FILE="${GZ_FILE}.sha256"
if [ -f "$SHA_FILE" ]; then
  echo "[restore] verifying checksum"
  if ! sha256sum -c "$SHA_FILE" --quiet; then
    echo "[restore] checksum mismatch — refusing to restore"
    exit 1
  fi
  echo "[restore] checksum ok"
else
  echo "[restore] no checksum sidecar; proceeding without verification"
fi

# Confirmation prompt unless --yes.
if [ "$CONFIRM" != "--yes" ]; then
  echo "==========================================="
  echo "  DANGER: this will OVERWRITE the database"
  echo "  backup file: $FILE"
  echo "  target db:   ${POSTGRES_DB:-docubot}"
  echo "==========================================="
  printf "type RESTORE to proceed: "
  read -r answer
  if [ "$answer" != "RESTORE" ]; then
    echo "[restore] aborted"
    exit 1
  fi
fi

echo "[restore] stopping app instances to prevent writes"
docker compose -f "$COMPOSE_FILE" stop app-blue app-green worker beat 2>/dev/null || true

echo "[restore] loading $GZ_FILE into postgres"
gunzip -c "$GZ_FILE" | docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "${POSTGRES_USER:-docubot}" -d "${POSTGRES_DB:-docubot}" -v ON_ERROR_STOP=1

echo "[restore] restarting app instances"
# --force-recreate so new containers read the current env.
# --no-deps so postgres/redis/nginx are not cascaded.
# --wait so compose waits for the healthcheck to pass before returning.
docker compose -f "$COMPOSE_FILE" up -d --wait --no-deps --force-recreate \
  app-blue worker beat 2>/dev/null || true
# Reload nginx so it re-resolves the upstream IP (the recreated
# app-blue container has a new IP that nginx has not cached).
docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload 2>/dev/null || true

echo "[restore] done"
