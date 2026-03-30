#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
TARGET="${1:-current}"

cd "$ROOT_DIR"

echo "[1/4] Build Python sidecar binary"
mkdir -p src-tauri/binaries
cd sidecar
"$PYTHON_BIN" -m pip install pyinstaller -q
"$PYTHON_BIN" -m pyinstaller main.py --onefile --name dictover-sidecar --distpath ../src-tauri/binaries/

cd "$ROOT_DIR"
echo "[2/4] Run tests"
cargo test --manifest-path src-tauri/Cargo.toml
if [[ -d "sidecar/tests" ]]; then
  "$PYTHON_BIN" -m pip install pytest -q
  "$PYTHON_BIN" -m pytest sidecar/tests/ -q
fi
npm install
npm run test:integration

echo "[3/4] Build Tauri app (target=$TARGET)"
if [[ "$TARGET" == "current" ]]; then
  npm run tauri build
else
  npm run tauri build -- --target "$TARGET"
fi

echo "[4/4] Build artifacts"
ls -la src-tauri/target/release/bundle || true
