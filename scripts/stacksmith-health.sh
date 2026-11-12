#!/usr/bin/env bash
# stacksmith-health.sh — one-command full-stack health check.
#
# Usage: bash scripts/stacksmith-health.sh [host]
#
# Checks every layer of the stack in order:
#   1. nginx is reachable
#   2. app liveness (/health/live/)
#   3. app readiness (/health/ready/) — postgres + redis
#   4. backup freshness (if textfile metric is available)
#   5. maintenance mode status
#
# Exits 0 if all checks pass, 1 if any fails.
set -euo pipefail

HOST="${1:-http://127.0.0.1:8080}"
pass=0
fail=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    printf "  \033[32m✓\033[0m %s\n" "$name"
    pass=$((pass + 1))
  else
    printf "  \033[31m✗\033[0m %s\n" "$name"
    fail=$((fail + 1))
  fi
}

echo "stacksmith health check — $HOST"
echo ""

check "nginx reachable" "curl -fsS -o /dev/null '$HOST/health/live/'"
check "app liveness (/health/live/)" "curl -fsS '$HOST/health/live/' | grep -q '\"alive\"'"
check "app readiness (/health/ready/)" "curl -fsS '$HOST/health/ready/' | grep -q '\"ready\"'"

# Check backup freshness if the metric file exists locally.
if [ -f monitoring/textfile/backup.prom ]; then
  ts=$(grep '^backup_last_success_timestamp_seconds' monitoring/textfile/backup.prom | awk '{print $2}')
  if [ -n "$ts" ] && [ "$ts" -gt 0 ]; then
    age_h=$(( ( $(date -u +%s) - ts ) / 3600 ))
    if [ "$age_h" -lt 26 ]; then
      printf "  \033[32m✓\033[0m backup freshness (%dh old, < 26h)\n" "$age_h"
      pass=$((pass + 1))
    else
      printf "  \033[31m✗\033[0m backup freshness (%dh old, > 26h)\n" "$age_h"
      fail=$((fail + 1))
    fi
  fi
else
  printf "  \033[33m-\033[0m backup freshness (no metric file, skipping)\n"
fi

# Check maintenance mode.
if [ -f monitoring/textfile/maintenance.prom ]; then
  if grep -q "stacksmith_maintenance_active 1" monitoring/textfile/maintenance.prom; then
    printf "  \033[33m!\033[0m maintenance mode is ON\n"
  else
    printf "  \033[32m✓\033[0m maintenance mode is OFF\n"
    pass=$((pass + 1))
  fi
else
  printf "  \033[32m✓\033[0m maintenance mode is OFF (no metric file)\n"
  pass=$((pass + 1))
fi

echo ""
echo "summary: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
