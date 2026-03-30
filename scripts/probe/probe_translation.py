from __future__ import annotations

import datetime as dt
import itertools
from typing import Any

from argos_bootstrap import install_required_argos_pairs
from common import dump_json
from translation_engines import ArgosEngine, NllbEngine, normalize_lang


LANGS = ["vi", "en", "zh-CN", "ja", "ko", "ru", "de", "fr", "fi"]

WORDS = {
    "vi": "xin chào",
    "en": "hello",
    "zh-CN": "你好",
    "ja": "こんにちは",
    "ko": "안녕",
    "ru": "привет",
    "de": "hallo",
    "fr": "bonjour",
    "fi": "hei",
}

SENTENCES = {
    "vi": "Hôm nay thời tiết rất đẹp, tôi muốn đi dạo.",
    "en": "The quick brown fox jumps over the lazy dog.",
    "zh-CN": "今天天气很好，我想出去走走。",
    "ja": "今日はとても良い天気で、散歩に行きたいです。",
    "ko": "오늘 날씨가 매우 좋아서 산책을 하고 싶습니다.",
    "ru": "Сегодня очень хорошая погода, я хочу прогуляться.",
    "de": "Heute ist das Wetter sehr schön, ich möchte spazieren gehen.",
    "fr": "Aujourd'hui le temps est très beau, je veux me promener.",
    "fi": "Tänään on hyvin kaunis sää, haluaisin lähteä kävelylle.",
}

SPECIAL_PAIRS = [
    ("vi", "en"),
    ("vi", "ja"),
    ("vi", "fi"),
    ("zh-CN", "ko"),
    ("ja", "ru"),
    ("en", "vi"),
]


def detect_languages() -> dict[str, Any]:
    try:
        from langdetect import detect
    except Exception as exc:
        return {"available": False, "error": str(exc), "results": []}
    results = []
    for lang, sentence in SENTENCES.items():
        detected = detect(sentence)
        normalized = "zh-CN" if detected.startswith("zh") else detected
        results.append(
            {
                "expected": lang,
                "detected": detected,
                "matched": normalized == lang,
            }
        )
    matched = sum(1 for item in results if item["matched"])
    return {
        "available": True,
        "error": None,
        "accuracy": round(matched / len(results), 4),
        "results": results,
    }


def benchmark_engine(engine: Any, source: str, target: str) -> dict[str, Any]:
    sentence = SENTENCES[source]
    paragraph = " ".join([sentence] * 8)
    outputs = {}
    for label, text in {
        "word": WORDS[source],
        "sentence": sentence,
        "paragraph_100w": paragraph,
    }.items():
        result = engine.translate(text, source, target)
        outputs[label] = {
            "ok": result.ok,
            "latency_ms": result.latency_ms,
            "mode": result.mode,
            "output_preview": result.text[:160],
            "output_len": len(result.text),
            "error": result.error,
        }
    return outputs


def build_argos_matrix(argos: ArgosEngine) -> list[dict[str, Any]]:
    matrix = []
    for source, target in itertools.permutations(LANGS, 2):
        matrix.append(
            {
                "source": source,
                "target": target,
                "direct": argos.supports_direct(source, target),
                "pivot_via_en": (not argos.supports_direct(source, target))
                and argos.supports_pivot(source, target),
            }
        )
    return matrix


def prepare_argos() -> tuple[ArgosEngine, dict[str, Any]]:
    argos = ArgosEngine()
    if not argos.available:
        return argos, {
            "attempted": 0,
            "installed": [],
            "missing_in_index": [],
            "install_errors": [],
            "error": argos.error,
        }
    required = set()
    for lang in LANGS:
        if lang == "en":
            continue
        required.add((normalize_lang(lang), "en"))
        required.add(("en", normalize_lang(lang)))
    report = install_required_argos_pairs(
        sorted(required), set(argos.installed_pairs())
    )
    refreshed = ArgosEngine()
    return refreshed, report


def main() -> None:
    argos, argos_install = prepare_argos()
    nllb = NllbEngine()

    argos_matrix = build_argos_matrix(argos) if argos.available else []
    argos_bench = {}
    for source, target in SPECIAL_PAIRS:
        argos_bench[f"{source}->{target}"] = benchmark_engine(argos, source, target)

    nllb_bench = {}
    for source, target in SPECIAL_PAIRS:
        nllb_bench[f"{source}->{target}"] = benchmark_engine(nllb, source, target)

    comparisons = []
    for pair, argos_outputs in argos_bench.items():
        nllb_outputs = nllb_bench.get(pair, {})
        for mode in ["word", "sentence", "paragraph_100w"]:
            a = argos_outputs.get(mode, {})
            n = nllb_outputs.get(mode, {})
            comparisons.append(
                {
                    "pair": pair,
                    "input_type": mode,
                    "argos_ok": a.get("ok"),
                    "argos_latency_ms": a.get("latency_ms"),
                    "nllb_ok": n.get("ok"),
                    "nllb_latency_ms": n.get("latency_ms"),
                }
            )

    long_text = " ".join([SENTENCES["vi"]] * 18)
    argos_long = argos.translate(long_text, "vi", "en")
    nllb_long = nllb.translate(long_text, "vi", "en")

    report = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "argos": {
            "available": argos.available,
            "error": argos.error,
            "bootstrap": argos_install,
            "installed_pairs": argos.installed_pairs(),
            "matrix": argos_matrix,
            "benchmarks": argos_bench,
            "long_text": {
                "input_chars": len(long_text),
                "ok": argos_long.ok,
                "output_len": len(argos_long.text),
                "latency_ms": argos_long.latency_ms,
                "mode": argos_long.mode,
                "error": argos_long.error,
            },
        },
        "nllb": {
            "available": nllb.available,
            "error": nllb.error,
            "model_id": nllb.model_id,
            "load_ms": nllb.load_ms,
            "memory_before_mb": nllb.mem_before_mb,
            "memory_after_mb": nllb.mem_after_mb,
            "benchmarks": nllb_bench,
            "long_text": {
                "input_chars": len(long_text),
                "ok": nllb_long.ok,
                "output_len": len(nllb_long.text),
                "latency_ms": nllb_long.latency_ms,
                "mode": nllb_long.mode,
                "error": nllb_long.error,
            },
        },
        "auto_detect": detect_languages(),
        "comparisons": comparisons,
    }
    dump_json(report)


if __name__ == "__main__":
    main()
