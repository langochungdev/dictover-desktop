#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
SIDECAR_PORT="${SIDECAR_PORT:-49152}"

cleanup() {
  if [[ -n "${SIDECAR_PID:-}" ]]; then
    kill "$SIDECAR_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

echo "[1/3] Start Python sidecar"
cd "$ROOT_DIR/sidecar"
"$PYTHON_BIN" -m pip install -r requirements.txt -q
"$PYTHON_BIN" -m uvicorn main:app --port "$SIDECAR_PORT" --reload &
SIDECAR_PID=$!

cd "$ROOT_DIR"
echo "[2/3] Install frontend deps"
npm install

echo "[3/3] Start Tauri dev"
SIDECAR_PORT="$SIDECAR_PORT" npm run tauri dev
