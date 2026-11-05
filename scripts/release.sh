#!/usr/bin/env bash
# release.sh — create an immutable release tag and manifest.
#
# Usage: bash scripts/release.sh [name]
#
# Produces:
#   - an annotated git tag: release-YYYYMMDD-HHMM (or the given name)
#   - a manifest file in releases/ with: git sha, image digests, env fingerprint
set -euo pipefail

RELEASES_DIR="releases"
mkdir -p "$RELEASES_DIR"

NAME="${1:-release-$(date -u +%Y%m%d-%H%M)}"
TAG="$NAME"

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "[release] tag $TAG already exists; refusing to overwrite"
  exit 1
fi

SHA="$(git rev-parse HEAD)"
SHORT_SHA="$(git rev-parse --short HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Image digests for the app image (best-effort; empty if not built yet).
APP_DIGEST="$(docker image inspect stacksmith/app:latest --format '{{index .RepoDigests 0}}' 2>/dev/null || echo "local-build")"

# Env fingerprint — a sha256 of the variable NAMES (not values) so the
# manifest records which knobs were configured without leaking secrets.
ENV_VARS="$(grep -vE '^\s*#|^\s*$' .env 2>/dev/null | cut -d= -f1 | sort | tr '\n' ',')"
ENV_FINGERPRINT="$(printf '%s' "$ENV_VARS" | sha256sum | cut -d' ' -f1)"

MANIFEST="$RELEASES_DIR/${TAG}.manifest"

cat > "$MANIFEST" <<EOF
release: $TAG
date: $DATE
git_sha: $SHA
git_short: $SHORT_SHA
branch: $BRANCH
app_image: stacksmith/app:latest
app_digest: $APP_DIGEST
env_fingerprint: $ENV_FINGERPRINT
env_vars: $ENV_VARS
EOF

git add "$MANIFEST"
git commit -m "chore(release): $TAG manifest" >/dev/null

# Re-read SHA after the manifest commit.
SHA="$(git rev-parse HEAD)"
git tag -a "$TAG" -m "Release $TAG ($SHORT_SHA)"

echo "[release] created $TAG"
echo "[release] manifest: $MANIFEST"
cat "$MANIFEST"
