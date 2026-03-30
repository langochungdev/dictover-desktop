#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
RUN_E2E="${RUN_E2E:-0}"

status=0

run_step() {
  local name="$1"
  shift
  echo "=== $name ==="
  if "$@"; then
    echo "PASS: $name"
  else
    echo "FAIL: $name"
    status=1
  fi
}

cd "$ROOT_DIR"

if command -v cargo >/dev/null 2>&1; then
  run_step "Rust unit tests" cargo test --manifest-path src-tauri/Cargo.toml
else
  echo "SKIP: Rust unit tests (cargo not found)"
fi

run_step "Python sidecar tests" bash -lc "\"$PYTHON_BIN\" -m pip install pytest -q && \"$PYTHON_BIN\" -m pytest sidecar/tests/ -v"
run_step "Frontend unit + integration tests" npm run test:integration

if [[ "$RUN_E2E" == "1" ]]; then
  run_step "E2E tests" npm run test:e2e
else
  echo "SKIP: E2E tests (set RUN_E2E=1 to enable)"
fi

echo "=== Summary ==="
if [[ "$status" -eq 0 ]]; then
  echo "All enabled test layers passed."
else
  echo "Some test layers failed."
fi

exit "$status"
