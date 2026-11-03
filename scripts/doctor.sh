#!/usr/bin/env bash
# Host readiness check: docker, compose, disk, memory.
set -euo pipefail

fail=0

step() { echo "[doctor] $*"; }

step "docker"
if command -v docker >/dev/null 2>&1; then
    docker --version
else
    echo "[doctor] MISSING: docker"
    fail=1
fi

step "compose plugin"
if docker compose version >/dev/null 2>&1; then
    docker compose version
else
    echo "[doctor] MISSING: docker compose plugin"
    fail=1
fi

step "disk space"
df -h . | tail -n 1

step "memory"
if command -v free >/dev/null 2>&1; then
    free -h | head -n 2
else
    echo "[doctor] free not available, skipping"
fi

if [ "$fail" -ne 0 ]; then
    echo "[doctor] host is NOT ready"
    exit 1
fi
echo "[doctor] host looks ready"
