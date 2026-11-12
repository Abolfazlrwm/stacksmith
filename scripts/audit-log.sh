#!/usr/bin/env bash
# audit-log.sh — append a timestamped entry to the deploy audit log.
#
# Usage: bash scripts/audit-log.sh <action> <details>
#
# Called by deploy.sh, rollback.sh, rotate-secrets.sh, and restore-db.sh
# to record who did what and when. The log is a simple append-only file
# (deploy/state/audit.log) with a JSON line per entry.
set -euo pipefail

AUDIT_LOG="deploy/state/audit.log"
ACTION="${1:?usage: audit-log.sh <action> <details>}"
DETAILS="${2:-}"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
USER="${USER:-unknown}"
HOST="$(hostname 2>/dev/null || echo unknown)"

mkdir -p "$(dirname "$AUDIT_LOG")"

# Append a JSON line.
jq -cn \
  --arg ts "$TIMESTAMP" \
  --arg action "$ACTION" \
  --arg details "$DETAILS" \
  --arg user "$USER" \
  --arg host "$HOST" \
  '{timestamp: $ts, action: $action, details: $details, user: $user, host: $host}' \
  >> "$AUDIT_LOG"

echo "[audit] logged: $ACTION — $DETAILS"
