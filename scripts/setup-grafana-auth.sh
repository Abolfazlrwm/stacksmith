#!/usr/bin/env bash
# setup-grafana-auth.sh — generate the htpasswd file for the grafana nginx location.
#
# Usage: bash scripts/setup-grafana-auth.sh <username> <password>
#
# Produces nginx/grafana.htpasswd with a bcrypt entry. The file is
# git-ignored (it contains a password hash).
set -euo pipefail

USER="${1:?usage: setup-grafana-auth.sh <username> <password>}"
PASS="${2:?usage: setup-grafana-auth.sh <username> <password>}"
OUT="nginx/grafana.htpasswd"

if ! command -v htpasswd >/dev/null 2>&1; then
  echo "[auth] htpasswd not found — install apache2-utils (apt install apache2-utils)"
  exit 1
fi

htpasswd -bcB "$OUT" "$USER" "$PASS"
chmod 644 "$OUT"

# Enable the grafana location if it is not already enabled.
if [ -f nginx/grafana.conf.disabled ]; then
  mv nginx/grafana.conf.disabled nginx/grafana.conf
  echo "[auth] enabled nginx/grafana.conf"
fi

echo "[auth] wrote $OUT"
echo "[auth] reload nginx: docker compose exec nginx nginx -s reload"
