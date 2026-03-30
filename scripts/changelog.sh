#!/usr/bin/env bash
set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository not found."
  exit 0
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REMOTE="origin/$BRANCH"

if git rev-parse --verify "$REMOTE" >/dev/null 2>&1; then
  UNPUSHED="$(git log "$REMOTE"..HEAD --oneline)"
else
  UNPUSHED="$(git log --oneline -20)"
fi

if [[ -z "$UNPUSHED" ]]; then
  echo "No new commits."
  exit 0
fi

echo "## Changelog"

echo "### Features"
echo "$UNPUSHED" | grep -E "^[a-f0-9]+\s+feat" | sed -E "s/^[a-f0-9]+\s+//" | sed 's/^/- /' || true

echo "### Bug Fixes"
echo "$UNPUSHED" | grep -E "^[a-f0-9]+\s+fix" | sed -E "s/^[a-f0-9]+\s+//" | sed 's/^/- /' || true

echo "### Docs"
echo "$UNPUSHED" | grep -E "^[a-f0-9]+\s+docs" | sed -E "s/^[a-f0-9]+\s+//" | sed 's/^/- /' || true

echo "### Chores"
echo "$UNPUSHED" | grep -E "^[a-f0-9]+\s+chore" | sed -E "s/^[a-f0-9]+\s+//" | sed 's/^/- /' || true
