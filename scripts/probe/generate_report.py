from __future__ import annotations

import json
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
REPORT = ROOT / "report.md"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fmt_ms(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"


def dictionary_section(data: dict) -> list[str]:
    rows = data.get("cases") or []
    lines = ["## 1. Dictionary API"]
    lines.append("| Word | Lang | Lookup | Latency (ms) | Missing Fields | Fallback |")
    lines.append("|---|---|---:|---:|---|---|")
    latencies = []
    for row in rows:
        lookup = row.get("lookup") or {}
        fields = row.get("fields") or {}
        missing = [k for k, ok in fields.items() if not ok]
        latencies.append(lookup.get("latency_ms", 0))
        lines.append(
            "| {word} | {lang} | {status} | {latency} | {missing} | {fallback} |".format(
                word=row.get("word"),
                lang=row.get("source_lang"),
                status=lookup.get("status_code"),
                latency=fmt_ms(lookup.get("latency_ms")),
                missing=", ".join(missing) if missing else "none",
                fallback="yes" if row.get("fallback_triggered") else "no",
            )
        )
    if latencies:
        lines.append("")
        lines.append(f"- Average lookup latency: {fmt_ms(mean(latencies))} ms")
    lines.append("")
    return lines


def translation_section(data: dict) -> list[str]:
    lines = ["## 2. Translation"]
    argos = data.get("argos") or {}
    nllb = data.get("nllb") or {}
    matrix = argos.get("matrix") or []
    pivot_pairs = [m for m in matrix if m.get("pivot_via_en")]
    direct_pairs = [m for m in matrix if m.get("direct")]
    lines.append(f"- Argos available: {argos.get('available')} (direct={len(direct_pairs)}, pivot={len(pivot_pairs)})")
    lines.append(f"- NLLB available: {nllb.get('available')} (load={fmt_ms(nllb.get('load_ms'))} ms)")
    lines.append(f"- NLLB RAM before/after load: {nllb.get('memory_before_mb')} MB -> {nllb.get('memory_after_mb')} MB")
    lines.append("")
    lines.append("### Pivot Pairs (Argos)")
    if pivot_pairs:
        for item in pivot_pairs[:40]:
            lines.append(f"- {item.get('source')} -> {item.get('target')} (via en)")
        if len(pivot_pairs) > 40:
            lines.append(f"- ... and {len(pivot_pairs) - 40} more")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("### Latency Comparison")
    lines.append("| Pair | Input | Argos OK | Argos ms | NLLB OK | NLLB ms |")
    lines.append("|---|---|---|---:|---|---:|")
    for row in data.get("comparisons") or []:
        lines.append(
            "| {pair} | {input_type} | {aok} | {ams} | {nok} | {nms} |".format(
                pair=row.get("pair"),
                input_type=row.get("input_type"),
                aok=row.get("argos_ok"),
                ams=fmt_ms(row.get("argos_latency_ms")),
                nok=row.get("nllb_ok"),
                nms=fmt_ms(row.get("nllb_latency_ms")),
            )
        )
    lines.append("")
    auto = data.get("auto_detect") or {}
    lines.append(f"- Auto-detect available: {auto.get('available')}, accuracy={auto.get('accuracy')}")
    lines.append("")
    return lines


def audio_section(data: dict) -> list[str]:
    lines = ["## 3. Audio"]
    cases = data.get("cases") or []
    chain = {}
    for row in cases:
        chain[row.get("chain_result")] = chain.get(row.get("chain_result"), 0) + 1
    for key, value in chain.items():
        lines.append(f"- {key}: {value} case(s)")
    swap = data.get("google_swap_regex_probe") or []
    swap_ok = sum(1 for x in swap if (x.get("probe") or {}).get("ok"))
    lines.append(f"- Google URL swap success variants: {swap_ok}/{len(swap)}")
    native = data.get("native_audio") or {}
    lines.append(f"- Native audio tools: mpv={native.get('mpv')} ffplay={native.get('ffplay')}")
    lines.append("- Web Speech API: manual runtime check required in Tauri WebView")
    lines.append("")
    return lines


def image_section(data: dict) -> list[str]:
    lines = ["## 4. Image Search"]
    rows = data.get("cases") or []
    ddg_ok = 0
    wiki_ok = 0
    for row in rows:
        if (row.get("duckduckgo") or {}).get("ok"):
            ddg_ok += 1
        if (row.get("wikipedia_search") or {}).get("ok"):
            wiki_ok += 1
    lines.append(f"- DuckDuckGo reachable in {ddg_ok}/{len(rows)} queries")
    lines.append(f"- Wikipedia search reachable in {wiki_ok}/{len(rows)} queries")
    lines.append("- Google CSE only runs when GOOGLE_CSE_KEY and GOOGLE_CSE_CX are provided")
    logic = data.get("ui_logic") or {}
    lines.append(f"- Cache TTL probe: {logic.get('ttl_seconds')} seconds")
    lines.append("- Infinite scroll threshold probe: 260px")
    lines.append("")
    return lines


def recommendation_section(translation: dict) -> list[str]:
    lines = ["## 5. Recommendation"]
    argos_available = bool((translation.get("argos") or {}).get("available"))
    nllb_available = bool((translation.get("nllb") or {}).get("available"))
    if argos_available and nllb_available:
        lines.append("- Use Argos as default for low-latency local translation.")
        lines.append("- Enable NLLB as quality mode for difficult language pairs.")
    elif argos_available:
        lines.append("- Use Argos as primary engine and rely on pivot via EN where needed.")
    elif nllb_available:
        lines.append("- Use NLLB as primary engine and cache model load on app startup.")
    else:
        lines.append("- Neither Argos nor NLLB is ready in this environment; install deps/models first.")
    lines.append("- Keep word lookup fallback enabled to guarantee minimal output on API failures.")
    lines.append("")
    return lines


def main() -> None:
    dictionary = load_json(RESULTS / "dict_report.json")
    translation = load_json(RESULTS / "translation_report.json")
    audio = load_json(RESULTS / "audio_report.json")
    image = load_json(RESULTS / "image_report.json")
    lines = ["# Step 1 Report", ""]
    lines += dictionary_section(dictionary)
    lines += translation_section(translation)
    lines += audio_section(audio)
    lines += image_section(image)
    lines += recommendation_section(translation)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {REPORT}")


if __name__ == "__main__":
    main()
