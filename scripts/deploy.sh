#!/usr/bin/env bash
# deploy.sh — blue-green deploy with nginx upstream switch and canary checks.
#
# Usage: bash scripts/deploy.sh [blue|green]
#
# Starts the inactive app color, waits for it to become healthy, switches
# the nginx upstream, reloads nginx, runs canary checks against the new
# color, then stops the old color after a grace period so in-flight
# requests drain.
#
# If the canary checks fail, the upstream is switched back to the old
# color and the deploy aborts (the new color is left running so logs can
# be inspected, but it serves no traffic).
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
UPSTREAMS="nginx/upstreams.conf"
GRACE_PERIOD="${GRACE_PERIOD:-10}"
CANARY_PROBES="${CANARY_PROBES:-5}"
CANARY_INTERVAL="${CANARY_INTERVAL:-2}"
NGINX_PORT="${NGINX_PORT:-8080}"

current_color() {
  grep -oE 'server app-[a-z]+:' "$UPSTREAMS" | head -1 | sed 's/server app-//; s/://'
}

next_color() {
  if [ "$1" = "blue" ]; then echo "green"; else echo "blue"; fi
}

switch_upstream() {
  local target="$1"
  cat > "$UPSTREAMS" <<EOF
# nginx upstreams — managed by scripts/deploy.sh. Do not edit by hand.
upstream app-backend {
    server app-${target}:8000;
}
EOF
  echo "[deploy] upstream switched to app-${target}"
}

reload_nginx() {
  echo "[deploy] reloading nginx"
  docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload
}

# canary_check: probe /health/live/ and /health/ready/ through nginx
# CANARY_PROBES times. Returns non-zero if any probe fails.
canary_check() {
  local ok=0
  local fail=0
  echo "[deploy] canary: $CANARY_PROBES probes, ${CANARY_INTERVAL}s apart"
  for i in $(seq 1 "$CANARY_PROBES"); do
    live="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${NGINX_PORT}/health/live/" || echo 000)"
    ready="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${NGINX_PORT}/health/ready/" || echo 000)"
    if [ "$live" = "200" ] && [ "$ready" = "200" ]; then
      ok=$((ok + 1))
      echo "[deploy] canary probe $i: live=$live ready=$ready OK"
    else
      fail=$((fail + 1))
      echo "[deploy] canary probe $i: live=$live ready=$ready FAIL"
    fi
    [ "$i" -lt "$CANARY_PROBES" ] && sleep "$CANARY_INTERVAL"
  done
  echo "[deploy] canary summary: $ok ok, $fail failed (of $CANARY_PROBES)"
  [ "$fail" -eq 0 ]
}

if [ ! -f "$UPSTREAMS" ]; then
  echo "[deploy] no upstream file; initial deploy as blue"
  switch_upstream "blue"
  ACTIVE="none"
else
  ACTIVE="$(current_color)"
fi

TARGET="${1:-$(next_color "$ACTIVE")}"

if [ "$TARGET" = "$ACTIVE" ]; then
  echo "[deploy] target ($TARGET) is already active; nothing to do"
  exit 0
fi

echo "[deploy] active=$ACTIVE target=$TARGET"

# 0. Verify image signature (if cosign is available and the image is from GHCR).
APP_IMAGE="${APP_IMAGE:-}"
if command -v cosign >/dev/null 2>&1 && echo "$APP_IMAGE" | grep -q "ghcr.io"; then
  echo "[deploy] verifying cosign signature on $APP_IMAGE"
  if cosign verify \
    --certificate-identity-regexp \
    "https://github.com/${GH_REPO:-Abolfazlrwm/stacksmith}/.github/.+" \
    --certificate-oidc-issuer \
    "https://token.actions.githubusercontent.com" \
    "$APP_IMAGE"; then
    echo "[deploy] signature verified"
  else
    echo "[deploy] ERROR: cosign verification failed — refusing to deploy"
    exit 1
  fi
else
  echo "[deploy] cosign not available or image is local — skipping verify"
fi

# 1. Start the target app instance.
echo "[deploy] starting app-$TARGET"
docker compose -f "$COMPOSE_FILE" up -d --wait --no-deps "app-$TARGET"

# 2. Switch the upstream and reload nginx.
switch_upstream "$TARGET"
reload_nginx

# 3. Canary checks against the new color through nginx.
if ! canary_check; then
  echo "[deploy] canary FAILED — rolling back upstream to app-$ACTIVE"
  if [ "$ACTIVE" != "none" ]; then
    switch_upstream "$ACTIVE"
    reload_nginx
  fi
  echo "[deploy] deploy aborted — app-$TARGET is still running (no traffic) for log inspection"
  exit 1
fi

# 4. Drain the old color after a grace period.
if [ "$ACTIVE" != "none" ]; then
  echo "[deploy] canary passed — waiting ${GRACE_PERIOD}s before stopping app-$ACTIVE"
  sleep "$GRACE_PERIOD"
  echo "[deploy] stopping app-$ACTIVE"
  docker compose -f "$COMPOSE_FILE" stop "app-$ACTIVE"
fi

echo "[deploy] done — app-$TARGET is live"
