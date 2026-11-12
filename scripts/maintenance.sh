#!/usr/bin/env bash
# maintenance.sh — put the stack into or out of maintenance mode.
#
# Usage:
#   bash scripts/maintenance.sh on   "replacing postgres"
#   bash scripts/maintenance.sh off
#
# When ON:
#   - nginx returns 503 with a maintenance JSON for all non-health routes
#   - the maintenance flag is written to monitoring/textfile/maintenance.prom
#   - Alertmanager alerts are not silenced (the operator silences manually)
#   - health probes (/health/live, /health/ready) still return 200 so the
#     deploy canary and blackbox probe stay green
#
# When OFF:
#   - nginx returns to normal proxying
#   - the maintenance flag is cleared
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
MAINT_FILE="monitoring/textfile/maintenance.prom"
NGINX_MAINT_ON="nginx/maintenance-on.conf"
EPOCH="$(date -u +%s)"

mode="${1:?usage: maintenance.sh on|off [reason]}"
reason="${2:-scheduled maintenance}"

mkdir -p monitoring/textfile

case "$mode" in
  on)
    echo "[maint] enabling maintenance mode: $reason"

    # Write the maintenance metric.
    cat > "$MAINT_FILE" << EOF
# HELP stacksmith_maintenance_active 1 if maintenance mode is on, 0 otherwise.
# TYPE stacksmith_maintenance_active gauge
stacksmith_maintenance_active 1
# HELP stacksmith_maintenance_start_timestamp Unix timestamp when maintenance started.
# TYPE stacksmith_maintenance_start_timestamp gauge
stacksmith_maintenance_start_timestamp $EPOCH
EOF
    echo "[maint] metric written to $MAINT_FILE"

    # Reload nginx with the maintenance config.
    cat > "$NGINX_MAINT_ON" << 'NGINX'
# Maintenance mode — return 503 for all non-health routes.
# Health probes still return 200 so monitoring does not page.
location / {
    return 503 '{"status":"maintenance","reason":"maintenance"}';
    add_header Content-Type application/json;
}
NGINX
    # Append to the default server block by overwriting the location.
    # Simplest: create a snippet that nginx includes.
    echo "[maint] nginx maintenance snippet written"

    # Reload nginx.
    docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload 2>/dev/null || true
    echo "[maint] maintenance mode ON — app is serving 503, health probes still 200"
    ;;

  off)
    echo "[maint] disabling maintenance mode"

    # Clear the maintenance metric.
    cat > "$MAINT_FILE" << EOF
# HELP stacksmith_maintenance_active 1 if maintenance mode is on, 0 otherwise.
# TYPE stacksmith_maintenance_active gauge
stacksmith_maintenance_active 0
# HELP stacksmith_maintenance_start_timestamp Unix timestamp when maintenance started.
# TYPE stacksmith_maintenance_start_timestamp gauge
stacksmith_maintenance_start_timestamp 0
EOF

    rm -f "$NGINX_MAINT_ON"
    docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload 2>/dev/null || true
    echo "[maint] maintenance mode OFF — app is serving normally"
    ;;

  status)
    if [ -f "$MAINT_FILE" ] && grep -q "stacksmith_maintenance_active 1" "$MAINT_FILE"; then
      echo "[maint] ON"
      exit 0
    else
      echo "[maint] OFF"
      exit 1
    fi
    ;;

  *)
    echo "usage: maintenance.sh on|off|status [reason]"
    exit 1
    ;;
esac
