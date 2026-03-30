from __future__ import annotations

try:
    from .dictionary import lookup_dictionary
    from .engines import TranslationResult, detect_language, normalize_lang, translate
except ImportError:
    from dictionary import lookup_dictionary
    from engines import TranslationResult, detect_language, normalize_lang, translate

__all__ = [
    "TranslationResult",
    "detect_language",
    "lookup_dictionary",
    "normalize_lang",
    "translate",
]
