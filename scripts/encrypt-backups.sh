#!/usr/bin/env bash
# encrypt-backups.sh — encrypt backup files with age before off-host copy.
#
# Usage: bash scripts/encrypt-backups.sh
#
# Reads BACKUP_AGE_RECIPIENT from .env (an age recipient, e.g. an SSH key
# or an age public key). Encrypts every docubot-*.sql.gz that does not
# already have a .age sidecar, producing docubot-*.sql.gz.age next to it.
# The original .gz and .sha256 are kept locally for the restore drill;
# only the .age files are shipped off-host by sync-backups.sh.
set -euo pipefail

BACKUP_DIR="backups"

if ! command -v age >/dev/null 2>&1; then
  echo "[encrypt] age not found on PATH — install age (apt install age, brew install age)"
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

if [ -z "${BACKUP_AGE_RECIPIENT:-}" ]; then
  echo "[encrypt] BACKUP_AGE_RECIPIENT not set in .env — generate a key with"
  echo "          'age-keygen -o age.key' and put the public key (age1...) in .env"
  exit 1
fi

if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR"/docubot-*.sql.gz 2>/dev/null)" ]; then
  echo "[encrypt] no backups to encrypt"
  exit 0
fi

encrypted=0
skipped=0
for gz in "$BACKUP_DIR"/docubot-*.sql.gz; do
  [ -e "$gz" ] || continue
  age_file="${gz}.age"
  if [ -f "$age_file" ]; then
    skipped=$((skipped + 1))
    continue
  fi
  echo "[encrypt] $gz → $age_file"
  age -r "$BACKUP_AGE_RECIPIENT" -o "$age_file" "$gz"
  encrypted=$((encrypted + 1))
done

echo "[encrypt] done — encrypted $encrypted, skipped $skipped (already had .age)"
