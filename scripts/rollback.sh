#!/usr/bin/env bash
# rollback.sh — roll back to the previous app color in one command.
#
# Usage: bash scripts/rollback.sh
#
# Reads the active color from the upstream file and deploys the other one.
# If the other color is not running (stopped after a deploy), it is started
# fresh; if it is still running, the switch is immediate.
set -euo pipefail

UPSTREAMS="nginx/upstreams.conf"

if [ ! -f "$UPSTREAMS" ]; then
  echo "[rollback] no upstream file; nothing to roll back"
  exit 1
fi

ACTIVE="$(grep -oE 'server app-[a-z]+:' "$UPSTREAMS" | head -1 | sed 's/server app-//; s/://')"

if [ -z "$ACTIVE" ]; then
  echo "[rollback] cannot determine active color"
  exit 1
fi

if [ "$ACTIVE" = "blue" ]; then
  TARGET="green"
else
  TARGET="blue"
fi

echo "[rollback] active=$ACTIVE → rolling back to $TARGET"
exec bash scripts/deploy.sh "$TARGET"
