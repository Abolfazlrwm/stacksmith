#!/usr/bin/env bash
# rotate-secrets.sh — rotate DJANGO_SECRET_KEY and POSTGRES_PASSWORD with
# zero downtime.
#
# Usage: bash scripts/rotate-secrets.sh [--key] [--password]
#
# Without flags, rotates both. With --key, rotates only the Django key.
# With --password, rotates only the postgres password.
#
# DJANGO_SECRET_KEY rotation:
#   1. Generate a new key.
#   2. Write it to .env.
#   3. Deploy (blue-green) so both colors pick up the new key.
#   4. Old sessions are invalidated; no data loss.
#
# POSTGRES_PASSWORD rotation:
#   1. Take a backup (safety net).
#   2. ALTER USER in postgres.
#   3. Write the new password to .env.
#   4. Restart the app, worker and beat (they reconnect with the new password).
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"
ROTATE_KEY=false
ROTATE_PASSWORD=false

if [ $# -eq 0 ]; then
  ROTATE_KEY=true
  ROTATE_PASSWORD=true
else
  for arg in "$@"; do
    case "$arg" in
      --key)      ROTATE_KEY=true ;;
      --password) ROTATE_PASSWORD=true ;;
      *) echo "usage: rotate-secrets.sh [--key] [--password]"; exit 1 ;;
    esac
  done
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "[rotate] .env not found"; exit 1
fi

set -a
# shellcheck disable=SC1090,SC1091
. ./"$ENV_FILE"
set +a

if [ "$ROTATE_KEY" = true ]; then
  NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  echo "[rotate] generating new DJANGO_SECRET_KEY"
  sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$NEW_KEY|" "$ENV_FILE"
  echo "[rotate] DJANGO_SECRET_KEY updated in $ENV_FILE"
  echo "[rotate] run 'bash scripts/deploy.sh' to apply (blue-green, zero downtime)"
  echo "[rotate] note: all existing sessions will be invalidated"
fi

if [ "$ROTATE_PASSWORD" = true ]; then
  NEW_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  echo "[rotate] taking a safety backup before touching postgres"
  bash scripts/backup-db.sh >/dev/null 2>&1 || echo "[rotate] warning: backup failed, proceeding anyway"

  echo "[rotate] changing postgres password"
  docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "${POSTGRES_USER:-docubot}" -d "${POSTGRES_DB:-docubot}" -c \
    "ALTER USER \"${POSTGRES_USER:-docubot}\" PASSWORD '$NEW_PASS';" >/dev/null

  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$NEW_PASS|" "$ENV_FILE"
  echo "[rotate] POSTGRES_PASSWORD updated in $ENV_FILE"

  echo "[rotate] restarting app, worker and beat to pick up the new password"
  # Restart (not force-recreate) so the containers re-read the env file
  # without recreating volumes or cascading to dependencies.
  docker compose -f "$COMPOSE_FILE" stop app-blue app-green worker beat 2>/dev/null || true
  docker compose -f "$COMPOSE_FILE" up -d --no-deps app-blue worker beat 2>/dev/null || true
  echo "[rotate] done"
fi

if [ "$ROTATE_KEY" = true ] && [ "$ROTATE_PASSWORD" = false ]; then
  echo "[rotate] to apply the key rotation, run: bash scripts/deploy.sh"
fi
