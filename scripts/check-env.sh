#!/usr/bin/env bash
# Fail loudly if the environment the stack needs is not there.
# Loads .env when present, then checks the required variables.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env"
    set +a
fi

missing=0
for var in SECRET_KEY POSTGRES_PASSWORD DOCUBOT_IMAGE; do
    if [ -z "${!var:-}" ]; then
        echo "[check-env] missing: $var"
        missing=1
    fi
done

if [ "$missing" -ne 0 ]; then
    echo "[check-env] set the missing variables in $ROOT/.env (see .env.example)"
    exit 1
fi

echo "[check-env] ok: SECRET_KEY, POSTGRES_PASSWORD, DOCUBOT_IMAGE are set"
