#!/usr/bin/env bash
# check-env.sh — verify all required env vars are set before bringing the stack up.
set -euo pipefail

required=(
  DJANGO_SECRET_KEY
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD
  POSTGRES_HOST
  POSTGRES_PORT
  REDIS_URL
)

if [ ! -f .env ]; then
  echo "check-env: .env not found — copy .env.example and fill it in"
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

missing=0
for var in "${required[@]}"; do
  val="${!var:-}"
  if [ -z "$val" ]; then
    echo "check-env: $var is not set"
    missing=$((missing + 1))
  fi
done

if [ "$missing" -gt 0 ]; then
  echo "check-env: $missing required variable(s) missing"
  exit 1
fi

if [ "$DJANGO_SECRET_KEY" = "change-me-to-a-50-char-random-string" ]; then
  echo "check-env: DJANGO_SECRET_KEY is still the placeholder — generate a real one"
  exit 1
fi

echo "check-env: all required variables set"
