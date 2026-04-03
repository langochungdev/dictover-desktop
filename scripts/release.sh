#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
WEB_VERSION_FILE="web/version.json"

if [[ -z "$VERSION" ]]; then
  echo "Usage: ./scripts/release.sh v1.0.0"
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository not found."
  exit 1
fi

cd "$ROOT_DIR"

echo "[1/4] Generate changelog"
CHANGELOG="$(bash scripts/changelog.sh)"

echo "[2/4] Update versions"
VERSION_PLAIN="${VERSION#v}"
sed -i -E "s/\"version\": \"[^\"]+\"/\"version\": \"$VERSION_PLAIN\"/" "$WEB_VERSION_FILE"
sed -i -E "s/\"version\": \"[^\"]+\"/\"version\": \"$VERSION_PLAIN\"/" src-tauri/tauri.conf.json
sed -i -E "s/^version = \"[^\"]+\"/version = \"$VERSION_PLAIN\"/" src-tauri/Cargo.toml
sed -i -E "s/\"version\": \"[^\"]+\"/\"version\": \"$VERSION_PLAIN\"/" package.json

echo "[3/4] Build installer"
bash scripts/build.sh

echo "[4/4] Tag and create release"
git add web/version.json src-tauri/tauri.conf.json src-tauri/Cargo.toml package.json
git commit -m "chore: release $VERSION"
git tag -a "$VERSION" -m "$CHANGELOG"
git push origin HEAD --tags

gh release create "$VERSION" \
  --title "DictOver $VERSION" \
  --notes "$CHANGELOG" \
  src-tauri/target/release/bundle/**/**
