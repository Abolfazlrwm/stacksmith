#!/usr/bin/env bash
# restore-db.sh — restore the database from a backup file with a pre-flight check.
#
# Usage: bash scripts/restore-db.sh <file> [--yes]
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

# Pre-flight: verify the sha256 checksum if a .sha256 sidecar exists.
SHA_FILE="${FILE}.sha256"
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

echo "[restore] loading $FILE into postgres"
gunzip -c "$FILE" | docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "${POSTGRES_USER:-docubot}" -d "${POSTGRES_DB:-docubot}" -v ON_ERROR_STOP=1

echo "[restore] restarting app instances"
docker compose -f "$COMPOSE_FILE" up -d --wait --no-deps app-blue 2>/dev/null || \
  docker compose -f "$COMPOSE_FILE" up -d --no-deps app-blue 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" up -d --no-deps worker beat 2>/dev/null || true

echo "[restore] done"
