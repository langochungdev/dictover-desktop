from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

try:
    from langdetect import detect
except Exception:
    detect = None


HTTP_TIMEOUT = 12
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "DictOver-Sidecar/0.1",
        "Accept": "application/json,text/plain,*/*",
    }
)

LANG_ALIAS = {"zh-CN": "zh", "zh": "zh"}


def normalize_lang(lang: str) -> str:
    return LANG_ALIAS.get(lang, lang)


@dataclass
class TranslationResult:
    result: str
    engine: str
    mode: str


class ArgosRuntime:
    def __init__(self) -> None:
        self.available = False
        self.error: str | None = None
        self._translate_module: Any = None
        self._direct_pairs: set[tuple[str, str]] = set()
        try:
            import argostranslate.package as apkg
            import argostranslate.translate as atranslate

            self._translate_module = atranslate
            for pkg in apkg.get_installed_packages():
                self._direct_pairs.add((pkg.from_code, pkg.to_code))
            self.available = True
        except Exception as exc:
            self.error = str(exc)

    def supports_direct(self, source: str, target: str) -> bool:
        return (normalize_lang(source), normalize_lang(target)) in self._direct_pairs

    def supports_pivot(self, source: str, target: str) -> bool:
        src = normalize_lang(source)
        tgt = normalize_lang(target)
        return (src, "en") in self._direct_pairs and ("en", tgt) in self._direct_pairs

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        if not self.available:
            raise RuntimeError(self.error or "Argos unavailable")
        src = normalize_lang(source)
        tgt = normalize_lang(target)
        if src == tgt:
            return TranslationResult(text, "argos", "identity")
        if self.supports_direct(src, tgt):
            output = self._translate_module.translate(text, src, tgt)
            return TranslationResult(output, "argos", "direct")
        if self.supports_pivot(src, tgt):
            step1 = self._translate_module.translate(text, src, "en")
            step2 = self._translate_module.translate(step1, "en", tgt)
            return TranslationResult(step2, "argos", "pivot")
        raise RuntimeError(f"Pair not installed: {src}->{tgt}")


ARGOS = ArgosRuntime()


def detect_language(text: str) -> str:
    if not text.strip():
        return "en"
    if detect is None:
        return "en"
    try:
        code = detect(text)
    except Exception:
        return "en"
    return "zh-CN" if code.startswith("zh") else code


def fallback_translate_api(text: str, source: str, target: str) -> TranslationResult:
    src = normalize_lang(source)
    tgt = normalize_lang(target)
    params = {"q": text, "langpair": f"{src}|{tgt}"}
    response = SESSION.get("https://api.mymemory.translated.net/get", params=params, timeout=HTTP_TIMEOUT)
    payload = response.json()
    translated = ((payload.get("responseData") or {}).get("translatedText")) or text
    return TranslationResult(translated, "mymemory", "api-fallback")


def translate(text: str, source: str, target: str) -> TranslationResult:
    if not text.strip():
        return TranslationResult("", "argos", "empty")
    src = detect_language(text) if source == "auto" else source
    tgt = target or "en"
    try:
        return ARGOS.translate(text, src, tgt)
    except Exception:
        return fallback_translate_api(text, src, tgt)
