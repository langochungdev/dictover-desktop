#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repository not found."
  exit 1
fi

chmod +x .githooks/pre-push

git config core.hooksPath .githooks

echo "Configured core.hooksPath to .githooks"
