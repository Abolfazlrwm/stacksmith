#!/usr/bin/env bash
# decrypt-backup.sh — decrypt an .age backup file back to a .sql.gz.
#
# Usage: bash scripts/decrypt-backup.sh <file.age> [output.sql.gz]
#
# Reads BACKUP_AGE_IDENTITY from .env (path to the age private key) or
# AGE_IDENTITY_FILE env var. Outputs to <file without .age> by default,
# or the second argument if given.
set -euo pipefail

INPUT="${1:?usage: decrypt-backup.sh <file.age> [output.sql.gz]}"
OUTPUT="${2:-${INPUT%.age}}"

if [ ! -f "$INPUT" ]; then
  echo "[decrypt] file not found: $INPUT"
  exit 1
fi

if ! command -v age >/dev/null 2>&1; then
  echo "[decrypt] age not found on PATH — install age"
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

IDENTITY="${AGE_IDENTITY_FILE:-${BACKUP_AGE_IDENTITY:-}}"
if [ -z "$IDENTITY" ] || [ ! -f "$IDENTITY" ]; then
  echo "[decrypt] age identity not found — set BACKUP_AGE_IDENTITY in .env to the key path"
  exit 1
fi

echo "[decrypt] $INPUT → $OUTPUT"
age -d -i "$IDENTITY" -o "$OUTPUT" "$INPUT"
echo "[decrypt] done"
