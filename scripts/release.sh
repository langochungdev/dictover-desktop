#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
WEB_VERSION_FILE="web/version.json"
CHANGELOG_FILE="CHANGELOG.md"
TMP_ENTRY="$(mktemp)"
TMP_TAIL="$(mktemp)"
TMP_NEW="$(mktemp)"

cleanup() {
  rm -f "$TMP_ENTRY" "$TMP_TAIL" "$TMP_NEW"
}

trap cleanup EXIT

if [[ -z "$VERSION" ]]; then
  echo "Usage: ./scripts/release.sh v1.0.0"
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository not found."
  exit 1
fi

cd "$ROOT_DIR"

if git rev-parse --verify "refs/tags/$VERSION" >/dev/null 2>&1; then
  echo "Tag already exists: $VERSION"
  exit 1
fi

LAST_TAG="$(git describe --tags --abbrev=0 2>/dev/null || true)"
RANGE="HEAD"
if [[ -n "$LAST_TAG" ]]; then
  RANGE="$LAST_TAG..HEAD"
fi

mapfile -t COMMIT_SUBJECTS < <(git log --reverse --pretty=format:%s "$RANGE")

if [[ ${#COMMIT_SUBJECTS[@]} -eq 0 ]]; then
  echo "No new commits to release."
  exit 0
fi

echo "[1/4] Update versions"
VERSION_PLAIN="${VERSION#v}"
sed -i -E "s/\"version\": \"[^\"]+\"/\"version\": \"$VERSION_PLAIN\"/" "$WEB_VERSION_FILE"
sed -i -E "s/\"version\": \"[^\"]+\"/\"version\": \"$VERSION_PLAIN\"/" src-tauri/tauri.conf.json
sed -i -E "s/^version = \"[^\"]+\"/version = \"$VERSION_PLAIN\"/" src-tauri/Cargo.toml
sed -i -E "s/\"version\": \"[^\"]+\"/\"version\": \"$VERSION_PLAIN\"/" package.json

echo "[2/4] Update changelog"
DATE_NOW="$(date +%Y-%m-%d)"
{
  echo "## $VERSION - $DATE_NOW"
  echo
  echo "### Commits"
  for subject in "${COMMIT_SUBJECTS[@]}"; do
    echo "- $subject"
  done
  echo
} > "$TMP_ENTRY"

if [[ -f "$CHANGELOG_FILE" ]]; then
  if grep -Eiq '^#[[:space:]]*changelog([[:space:]]*)$' "$CHANGELOG_FILE"; then
    tail -n +2 "$CHANGELOG_FILE" > "$TMP_TAIL"
    {
      echo "# Changelog"
      echo
      cat "$TMP_ENTRY"
      cat "$TMP_TAIL"
    } > "$CHANGELOG_FILE"
  else
    {
      echo "# Changelog"
      echo
      cat "$TMP_ENTRY"
      cat "$CHANGELOG_FILE"
    } > "$TMP_NEW"
    mv "$TMP_NEW" "$CHANGELOG_FILE"
  fi
else
  {
    echo "# Changelog"
    echo
    cat "$TMP_ENTRY"
  } > "$CHANGELOG_FILE"
fi

echo "[3/4] Sync web release metadata"
node scripts/sync-web-release.mjs

echo "[4/4] Commit and tag"
git add CHANGELOG.md web/version.json web/releases/latest.json src-tauri/tauri.conf.json src-tauri/Cargo.toml package.json
git commit -m "chore: release $VERSION"
git tag -a "$VERSION" -m "DictOver $VERSION"

echo "Release commit and tag created: $VERSION"
echo "Push when ready: git push origin HEAD --tags"
