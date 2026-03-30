# DictOver Desktop (Tauri 2)

Desktop app port từ DictOver Anki add-on, tập trung vào 2 tính năng cốt lõi:
- Popover tra cứu/dịch khi chọn chữ.
- Hotkey dịch nhanh nội dung trong field.

Project dùng kiến trúc 3 lớp:
- Frontend: React + TypeScript (Vite)
- Backend desktop: Rust + Tauri 2
- Translation sidecar: Python + FastAPI

## Trạng thái hiện tại

- Step 1: Hoàn thành probe + report khả thi API/translation/audio/image.
- Step 2: Hoàn thành skeleton app, settings UI, sidecar bridge, scripts build/release, CI/CD.
- Step 3: Hoàn thành test layers (Rust unit, Python unit/API, frontend integration, e2e scaffold).

## Cấu trúc chính

- `src/`: frontend UI, hooks, services
- `src-tauri/`: Rust commands, config persistence, hotkey bridge
- `sidecar/`: FastAPI `/translate` và `/lookup`
- `scripts/`: dev/build/release/test-all/probe
- `tests/`: integration + e2e specs
- `results/`, `report.md`: output từ Step 1 feasibility

## Chạy nhanh (dev)

Yêu cầu:
- Node.js 20+
- Python 3.11+
- Rust toolchain (để chạy Tauri đầy đủ)

Cài frontend deps:

```bash
npm install
```

Cài sidecar deps:

```bash
python -m pip install -r sidecar/requirements.txt
```

Chạy sidecar:

```bash
cd sidecar
python -m uvicorn main:app --port 49152 --reload
```

Chạy frontend:

```bash
npm run dev
```

Chạy Tauri app:

```bash
npm run tauri dev
```

## Settings hỗ trợ (13 keys)

- `enable_lookup`
- `enable_translate`
- `enable_audio`
- `auto_play_audio_mode`
- `popover_trigger_mode`
- `popover_shortcut`
- `source_language`
- `target_language`
- `max_definitions`
- `show_example`
- `popover_open_panel_mode`
- `popover_definition_language_mode`
- `hotkey_translate_shortcut`

## Testing

Chạy nhanh tất cả lớp test khả dụng:

```bash
bash scripts/test-all.sh
```

Lưu ý:
- Nếu máy chưa cài Rust (`cargo`), lớp test Rust sẽ tự skip.
- E2E mặc định skip, bật bằng:

```bash
RUN_E2E=1 bash scripts/test-all.sh
```

Các lệnh riêng:

```bash
npm run test:integration
python -m pytest sidecar/tests/ -v
cargo test --manifest-path src-tauri/Cargo.toml
npm run test:e2e
```

## Build / Release

Build local:

```bash
bash scripts/build.sh
```

Release tag:

```bash
bash scripts/release.sh v1.0.0
```

## CI/CD

- `.github/workflows/test.yml`: chạy test khi push/PR
- `.github/workflows/release.yml`: build/release khi push tag `v*`

## Ghi chú kỹ thuật

- Nhiều ngôn ngữ Wiktionary domain trả 501 cho REST endpoint; luồng lookup đã fallback qua `en.wiktionary.org`.
- Argos được dùng làm default engine, hỗ trợ pivot qua EN; NLLB giữ vai trò quality mode.
- Audio fallback chain giữ nguyên theo kế hoạch: dictionary audio -> URL swap -> native audio -> speech synthesis.
