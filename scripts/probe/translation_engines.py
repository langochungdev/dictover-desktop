from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any


LANG_ALIAS = {"zh-CN": "zh", "zh": "zh"}
NLLB_CODE = {
    "vi": "vie_Latn",
    "en": "eng_Latn",
    "zh-CN": "zho_Hans",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "ru": "rus_Cyrl",
    "de": "deu_Latn",
    "fr": "fra_Latn",
    "fi": "fin_Latn",
}


def normalize_lang(lang: str) -> str:
    return LANG_ALIAS.get(lang, lang)


def now_ms() -> float:
    return time.perf_counter() * 1000.0


def process_mem_mb() -> float | None:
    try:
        import psutil

        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return None


@dataclass
class ProbeResult:
    ok: bool
    text: str
    latency_ms: float
    mode: str
    error: str | None = None


class ArgosEngine:
    def __init__(self) -> None:
        self.available = False
        self.error: str | None = None
        self._langs: dict[str, Any] = {}
        self._direct_pairs: set[tuple[str, str]] = set()
        self._atranslate: Any = None
        try:
            import argostranslate.package as apkg
            import argostranslate.translate as atranslate

            self._atranslate = atranslate
            langs = atranslate.get_installed_languages()
            self._langs = {lang.code: lang for lang in langs}
            for pkg in apkg.get_installed_packages():
                self._direct_pairs.add((pkg.from_code, pkg.to_code))
            self.available = True
        except Exception as exc:
            self.error = str(exc)

    def installed_pairs(self) -> list[tuple[str, str]]:
        return sorted(self._direct_pairs)

    def supports_direct(self, source: str, target: str) -> bool:
        src = normalize_lang(source)
        tgt = normalize_lang(target)
        return (src, tgt) in self._direct_pairs

    def supports_pivot(self, source: str, target: str) -> bool:
        src = normalize_lang(source)
        tgt = normalize_lang(target)
        return (src, "en") in self._direct_pairs and ("en", tgt) in self._direct_pairs

    def translate(self, text: str, source: str, target: str) -> ProbeResult:
        if not self.available:
            return ProbeResult(False, "", 0.0, "unavailable", self.error)
        src = normalize_lang(source)
        tgt = normalize_lang(target)
        if src == tgt:
            return ProbeResult(True, text, 0.0, "identity")
        start = now_ms()
        try:
            if self.supports_direct(src, tgt):
                translated = self._atranslate.translate(text, src, tgt)
                return ProbeResult(
                    True, translated, round(now_ms() - start, 2), "direct"
                )
            if self.supports_pivot(src, tgt):
                step1 = self._atranslate.translate(text, src, "en")
                step2 = self._atranslate.translate(step1, "en", tgt)
                return ProbeResult(True, step2, round(now_ms() - start, 2), "pivot")
            return ProbeResult(
                False,
                "",
                round(now_ms() - start, 2),
                "unsupported",
                "pair-not-installed",
            )
        except Exception as exc:
            return ProbeResult(False, "", round(now_ms() - start, 2), "error", str(exc))


class NllbEngine:
    def __init__(self) -> None:
        self.available = False
        self.error: str | None = None
        self.model_id = os.getenv("NLLB_MODEL_ID", "facebook/nllb-200-distilled-600M")
        self.load_ms = 0.0
        self.mem_before_mb: float | None = None
        self.mem_after_mb: float | None = None
        self._model: Any = None
        self._tokenizer: Any = None

    def load(self) -> None:
        if self.available or self.error:
            return
        start = now_ms()
        self.mem_before_mb = process_mem_mb()
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id)
            self.available = True
            self.load_ms = round(now_ms() - start, 2)
            self.mem_after_mb = process_mem_mb()
        except Exception as exc:
            self.error = str(exc)
            self.load_ms = round(now_ms() - start, 2)
            self.mem_after_mb = process_mem_mb()

    def supports(self, source: str, target: str) -> bool:
        return source in NLLB_CODE and target in NLLB_CODE

    def translate(self, text: str, source: str, target: str) -> ProbeResult:
        self.load()
        if not self.available:
            return ProbeResult(False, "", 0.0, "unavailable", self.error)
        if not self.supports(source, target):
            return ProbeResult(False, "", 0.0, "unsupported", "unsupported-lang")
        if source == target:
            return ProbeResult(True, text, 0.0, "identity")
        start = now_ms()
        try:
            src_code = NLLB_CODE[source]
            tgt_code = NLLB_CODE[target]
            self._tokenizer.src_lang = src_code
            inputs = self._tokenizer(text, return_tensors="pt", truncation=True)
            forced_id = self._tokenizer.convert_tokens_to_ids(tgt_code)
            outputs = self._model.generate(
                **inputs, forced_bos_token_id=forced_id, max_new_tokens=512
            )
            decoded = self._tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            return ProbeResult(True, decoded, round(now_ms() - start, 2), "direct")
        except Exception as exc:
            return ProbeResult(False, "", round(now_ms() - start, 2), "error", str(exc))
