#!/usr/bin/env bash
# deploy.sh — blue-green deploy with nginx upstream switch.
#
# Usage: bash scripts/deploy.sh [blue|green]
#
# Starts the inactive app color, waits for it to become healthy, switches
# the nginx upstream, reloads nginx, then stops the old color after a
# grace period so in-flight requests drain.
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
UPSTREAMS="nginx/upstreams.conf"
GRACE_PERIOD="${GRACE_PERIOD:-10}"

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

# 1. Start the target app instance.
echo "[deploy] starting app-$TARGET"
docker compose -f "$COMPOSE_FILE" up -d --wait --no-deps "app-$TARGET"

# 2. Switch the upstream and reload nginx.
switch_upstream "$TARGET"
reload_nginx

# 3. Drain the old color after a grace period.
if [ "$ACTIVE" != "none" ]; then
  echo "[deploy] waiting ${GRACE_PERIOD}s before stopping app-$ACTIVE"
  sleep "$GRACE_PERIOD"
  echo "[deploy] stopping app-$ACTIVE"
  docker compose -f "$COMPOSE_FILE" stop "app-$ACTIVE"
fi

echo "[deploy] done — app-$TARGET is live"
