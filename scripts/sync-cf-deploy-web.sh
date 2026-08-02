#!/usr/bin/env bash
# Push only the Astro site to origin/cf-deploy-web for Cloudflare.
# Full monorepo is ~6GB (verse/chapter mp3s) and CF clone times out.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB="$ROOT/web"
TMP="${TMPDIR:-/tmp}/hb-cf-deploy-$$"
REMOTE="$(cd "$ROOT" && git remote get-url origin)"
BRANCH="cf-deploy-web"

cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

rm -rf "$TMP"
mkdir -p "$TMP"
# copy site sources (no node_modules/dist)
tar -C "$WEB" \
  --exclude=node_modules --exclude=dist --exclude=.astro \
  -cf - . | tar -C "$TMP" -xf -

cd "$TMP"
git init -b "$BRANCH" >/dev/null
git -c user.email='moses@heybible.org' -c user.name='Moses' add -A
if git -c user.email='moses@heybible.org' -c user.name='Moses' diff --cached --quiet; then
  echo "nothing to commit"
else
  MSG="${1:-deploy: sync podcast web to cf-deploy-web}"
  git -c user.email='moses@heybible.org' -c user.name='Moses' commit -m "$MSG" >/dev/null
fi
git remote add origin "$REMOTE"
git push -u origin "HEAD:$BRANCH" --force
echo "Pushed $BRANCH → $REMOTE ($BRANCH)"
echo "Cloudflare should build this branch with root directory = / (repo root of the branch)"
