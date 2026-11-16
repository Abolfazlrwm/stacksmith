#!/usr/bin/env bash
# test_deploy_verify.sh — prove the cosign-at-deploy gate fires correctly.
#
# This is a unit test for the cosign-verify branch of scripts/deploy.sh,
# NOT a full deploy drill. It stubs `cosign verify` so we can assert both
# the success path (verify passes → deploy proceeds past the gate) and the
# failure path (verify fails → deploy refuses to continue) without needing
# a real signed image, GHCR credentials, or a running stack.
#
# Usage: bash scripts/test_deploy_verify.sh
#
# Exit codes: 0 if both paths behave correctly, 1 otherwise.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
DEPLOY="$REPO_ROOT/scripts/deploy.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- fixtures ---------------------------------------------------------------
# A minimal upstreams.conf so deploy.sh's current_color() works.
mkdir -p "$TMP/nginx"
cat > "$TMP/nginx/upstreams.conf" <<'EOF'
upstream app-backend {
    server app-blue:8000;
}
EOF

# A stub compose file that does nothing — we never reach the docker steps
# because the verify gate runs first and (in the failure case) exits.
cat > "$TMP/docker-compose.prod.yml" <<'EOF'
services:
  app-blue: {image: nginx}
EOF

# A stub cosign that always "succeeds" — used to prove the success path.
cat > "$TMP/cosign-ok" <<'EOF'
#!/usr/bin/env bash
echo "[stub-cosign] verify ok: $*"
exit 0
EOF

# A stub cosign that always "fails" — used to prove the failure path.
cat > "$TMP/cosign-fail" <<'EOF'
#!/usr/bin/env bash
echo "[stub-cosign] verify FAILED: $*" >&2
exit 1
EOF
chmod +x "$TMP/cosign-ok" "$TMP/cosign-fail"

PASS=0
FAIL=0

run_deploy() {
  # Run deploy.sh with our PATH shimmed so `command -v cosign` finds the stub,
  # and with COMPOSE_FILE pointing at our no-op stub so the gate runs in
  # isolation. We capture exit code without `set -e` killing us.
  # Target is `green` because the active upstream in our fixture is `blue`,
  # so the deploy proceeds past the "already active" early-exit.
  set +e
  ( cd "$TMP" && \
      PATH="$TMP:$PATH" \
      APP_IMAGE="$1" \
      COMPOSE_FILE="docker-compose.prod.yml" \
      UPSTREAMS="nginx/upstreams.conf" \
      bash "$DEPLOY" green ) >"$TMP/out.log" 2>"$TMP/err.log"
  echo $?
  set -e
}

echo "[test] case 1: cosign verify succeeds → deploy proceeds past the gate"
# Point `cosign` on PATH at the success stub for this case.
ln -sf "$TMP/cosign-ok" "$TMP/cosign"
rc=$(run_deploy "ghcr.io/abolfazlrwm/stacksmith/app:v1.2.0")
# Deploy will fail later (no real docker stack), but it MUST have passed
# the cosign gate first. We assert by looking for the success message.
if grep -q "signature verified" "$TMP/out.log"; then
  echo "  PASS: gate passed on a verified image"
  PASS=$((PASS + 1))
else
  echo "  FAIL: gate did not report success"
  echo "  --- stdout ---"; cat "$TMP/out.log"
  echo "  --- stderr ---"; cat "$TMP/err.log"
  FAIL=$((FAIL + 1))
fi

# Make the stub cosign fail for the next case.
ln -sf "$TMP/cosign-fail" "$TMP/cosign"

echo ""
echo "[test] case 2: cosign verify fails → deploy refuses to continue"
rc=$(run_deploy "ghcr.io/abolfazlrwm/stacksmith/app:v1.2.0")
if [ "$rc" -ne 0 ] && grep -q "cosign verification failed" "$TMP/out.log"; then
  echo "  PASS: deploy aborted with the right exit code ($rc) and message"
  PASS=$((PASS + 1))
else
  echo "  FAIL: deploy did not abort on verify failure (rc=$rc)"
  echo "  --- stdout ---"; cat "$TMP/out.log"
  echo "  --- stderr ---"; cat "$TMP/err.log"
  FAIL=$((FAIL + 1))
fi

# Restore the success stub for the local-image-skip case.
ln -sf "$TMP/cosign-ok" "$TMP/cosign"

echo ""
echo "[test] case 3: non-GHCR image → gate is skipped (no cosign needed)"
rc=$(run_deploy "stacksmith/app:latest")
if grep -q "skipping verify" "$TMP/out.log"; then
  echo "  PASS: gate skipped for a local image"
  PASS=$((PASS + 1))
else
  echo "  FAIL: gate did not skip for a local image"
  echo "  --- stdout ---"; cat "$TMP/out.log"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "[summary] $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
