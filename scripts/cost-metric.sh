#!/usr/bin/env bash
# cost-metric.sh — estimate monthly VPS cost and write a textfile metric.
#
# Usage: bash scripts/cost-metric.sh
#
# Writes monitoring/textfile/cost.prom with:
#   stacksmith_cost_estimate_usd  — estimated monthly cost
#   stacksmith_cost_per_cpu_hour  — cost per CPU-hour (for per-service breakdown)
#
# The estimate is based on the VPS plan price set in COST_VPS_MONTHLY_USD
# (default: 8.0 for a typical 4 vCPU / 8 GB VPS).
set -euo pipefail

TEXTFILE_DIR="monitoring/textfile"
METRIC_FILE="$TEXTFILE_DIR/cost.prom"
COST_VPS_MONTHLY_USD="${COST_VPS_MONTHLY_USD:-8.0}"

# Count CPU cores (for per-CPU-hour breakdown).
CPU_COUNT=$(nproc 2>/dev/null || echo 1)
COST_PER_CPU_HOUR=$(echo "scale=6; $COST_VPS_MONTHLY_USD / ($CPU_COUNT * 24 * 30)" | bc 2>/dev/null || echo "0.011")

mkdir -p "$TEXTFILE_DIR"
cat > "$METRIC_FILE" << EOF
# HELP stacksmith_cost_estimate_usd Estimated monthly VPS cost in USD.
# TYPE stacksmith_cost_estimate_usd gauge
stacksmith_cost_estimate_usd $COST_VPS_MONTHLY_USD
# HELP stacksmith_cost_per_cpu_hour Cost per CPU-hour for per-service breakdown.
# TYPE stacksmith_cost_per_cpu_hour gauge
stacksmith_cost_per_cpu_hour $COST_PER_CPU_HOUR
EOF

echo "[cost] wrote $METRIC_FILE (monthly=\$$COST_VPS_MONTHLY_USD, cpu/h=\$$COST_PER_CPU_HOUR)"
