from __future__ import annotations

import re
from typing import Any
from difflib import SequenceMatcher
from urllib.parse import quote

try:
    from .dictionary import lookup_dictionary
    from .engines import (
        TranslationResult,
        detect_language,
        fallback_translate_api,
        is_single_word_text,
        normalize_lang,
        query_datamuse_word,
        translate,
    )
except ImportError:
    from dictionary import lookup_dictionary
    from engines import (
        TranslationResult,
        detect_language,
        fallback_translate_api,
        is_single_word_text,
        normalize_lang,
        query_datamuse_word,
        translate,
    )


LANG_TO_TTS = {
    "zh-CN": "zh-CN",
    "zh": "zh-CN",
}


def _normalize_tts_lang(lang: str) -> str:
    normalized = str(lang or "en").strip()
    return LANG_TO_TTS.get(normalized, normalized or "en")


def _build_google_tts_url(text: str, lang: str) -> str:
    query = str(text or "").strip()
    if not query:
        return ""
    tts_lang = _normalize_tts_lang(lang)
    encoded = quote(query)
    return (
        "https://translate.google.com/translate_tts"
        f"?ie=UTF-8&client=tw-ob&tl={quote(tts_lang)}&q={encoded}"
    )


def _normalize_word_candidate(text: str) -> str:
    compact = " ".join((text or "").split()).strip()
    if not compact:
        return ""
    return re.sub(r"^[^\w]+|[^\w]+$", "", compact, flags=re.UNICODE)


def _translate_terms(
    terms: list[str],
    source: str,
    target: str,
    limit: int = 6,
    fallback_to_source: bool = False,
) -> list[str]:
    translated_terms: list[str] = []
    source_terms: list[str] = []
    for term in terms[:limit]:
        cleaned = _normalize_word_candidate(term)
        if not cleaned:
            continue
        if cleaned.lower() not in {item.lower() for item in source_terms}:
            source_terms.append(cleaned)
        try:
            translated = translate(cleaned, source, target).result
            normalized = _normalize_word_candidate(translated)
        except Exception:
            continue
        if not normalized:
            continue
        if normalized.lower() in {item.lower() for item in translated_terms}:
            continue
        translated_terms.append(normalized)
    if translated_terms:
        return translated_terms
    if fallback_to_source:
        return source_terms[:limit]
    return translated_terms


def _extract_audio_lang(payload: dict[str, Any], fallback_lang: str) -> str:
    raw = payload.get("audio_lang") if isinstance(payload, dict) else None
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return fallback_lang


def _normalized_compare_text(text: str) -> str:
    return "".join(str(text or "").lower().split())


def _score_candidate_translation(
    candidate: str, target: str, source: str, original: str
) -> float:
    cleaned_candidate = _normalize_word_candidate(candidate)
    cleaned_original = _normalize_word_candidate(original)
    if not cleaned_candidate or not cleaned_original:
        return -1.0

    try:
        back = fallback_translate_api(cleaned_candidate, target, source).result
    except Exception:
        return -1.0

    back_norm = _normalized_compare_text(back)
    original_norm = _normalized_compare_text(cleaned_original)
    if not back_norm or not original_norm:
        return -1.0

    similarity = SequenceMatcher(None, original_norm, back_norm).ratio()
    if len(cleaned_candidate) <= 2:
        similarity -= 0.12
    if len(cleaned_candidate) >= 4:
        similarity += 0.05
    if cleaned_candidate.lower() == cleaned_original.lower():
        similarity -= 0.1
    return similarity


def _choose_single_word_translation(
    cleaned: str, source: str, target: str
) -> TranslationResult:
    primary = translate(cleaned, source, target)
    candidates: list[TranslationResult] = [primary]

    try:
        api_candidate = fallback_translate_api(cleaned, source, target)
        if _normalized_compare_text(api_candidate.result) != _normalized_compare_text(
            primary.result
        ):
            candidates.append(api_candidate)
    except Exception:
        pass

    best = primary
    best_score = _score_candidate_translation(primary.result, target, source, cleaned)

    for candidate in candidates[1:]:
        score = _score_candidate_translation(candidate.result, target, source, cleaned)
        if score > best_score:
            best = candidate
            best_score = score

    return best


def _build_word_data(translated_word: str, target: str) -> dict[str, Any] | None:
    lookup_word = _normalize_word_candidate(translated_word)
    if not lookup_word or not is_single_word_text(lookup_word):
        return None

    phonetic: str | None = None
    audio_url: str | None = None
    audio_lang = target
    part_of_speech: str | None = None

    try:
        dictionary = lookup_dictionary(lookup_word, target)
        phonetic = (
            dictionary.get("phonetic")
            if isinstance(dictionary.get("phonetic"), str)
            else None
        )
        audio_url = (
            dictionary.get("audio_url")
            if isinstance(dictionary.get("audio_url"), str)
            else None
        )
        audio_lang = _extract_audio_lang(dictionary, target)
        meanings = dictionary.get("meanings") if isinstance(dictionary, dict) else None
        if isinstance(meanings, list):
            for meaning in meanings:
                if not isinstance(meaning, dict):
                    continue
                candidate = meaning.get("part_of_speech")
                if isinstance(candidate, str) and candidate.strip():
                    part_of_speech = candidate.strip()
                    break
    except Exception:
        dictionary = None

    synonyms: list[str] = []
    related: list[str] = []
    sounds_like: list[str] = []

    if target == "en":
        try:
            datamuse = query_datamuse_word(lookup_word)
            synonyms = datamuse.get("synonyms") or []
            related = datamuse.get("related") or []
            sounds_like = datamuse.get("sounds_like") or []
        except Exception:
            pass
    else:
        pivot_word = ""
        try:
            pivot_result = translate(lookup_word, target, "en")
            pivot_word = _normalize_word_candidate(pivot_result.result)
        except Exception:
            pivot_word = ""

        if pivot_word and is_single_word_text(pivot_word):
            try:
                datamuse = query_datamuse_word(pivot_word)
                pivot_synonyms = datamuse.get("synonyms") or []
                pivot_related = datamuse.get("related") or []
                pivot_sounds_like = datamuse.get("sounds_like") or []
                synonyms = _translate_terms(
                    pivot_synonyms,
                    "en",
                    target,
                    limit=6,
                    fallback_to_source=True,
                )
                related = _translate_terms(
                    pivot_related,
                    "en",
                    target,
                    limit=6,
                    fallback_to_source=True,
                )
                sounds_like = _translate_terms(
                    pivot_sounds_like,
                    "en",
                    target,
                    limit=6,
                    fallback_to_source=True,
                )
            except Exception:
                pass

            if not phonetic or not audio_url:
                try:
                    english_dict = lookup_dictionary(pivot_word, "en")
                    if not phonetic:
                        phonetic = (
                            english_dict.get("phonetic")
                            if isinstance(english_dict.get("phonetic"), str)
                            else phonetic
                        )
                    if not audio_url:
                        audio_url = (
                            english_dict.get("audio_url")
                            if isinstance(english_dict.get("audio_url"), str)
                            else audio_url
                        )
                    if not part_of_speech:
                        meanings = (
                            english_dict.get("meanings")
                            if isinstance(english_dict, dict)
                            else None
                        )
                        if isinstance(meanings, list):
                            for meaning in meanings:
                                if not isinstance(meaning, dict):
                                    continue
                                candidate = meaning.get("part_of_speech")
                                if isinstance(candidate, str) and candidate.strip():
                                    part_of_speech = candidate.strip()
                                    break
                    if audio_url:
                        audio_lang = _extract_audio_lang(english_dict, "en")
                except Exception:
                    pass

    if not audio_url:
        fallback_audio_url = _build_google_tts_url(lookup_word, target)
        if fallback_audio_url:
            audio_url = fallback_audio_url
            audio_lang = target

    has_extra = bool(
        phonetic or audio_url or part_of_speech or synonyms or related or sounds_like
    )
    if not has_extra:
        return None

    return {
        "input": lookup_word,
        "phonetic": phonetic,
        "part_of_speech": part_of_speech,
        "audio_url": audio_url,
        "audio_lang": audio_lang,
        "synonyms": synonyms,
        "related": related,
        "sounds_like": sounds_like,
    }


def _resolve_english_anchor_word(
    source_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str,
) -> str:
    normalized_source = normalize_lang(source_lang)
    normalized_target = normalize_lang(target_lang)

    if normalized_source == "en":
        source_word = _normalize_word_candidate(source_text)
        if source_word and is_single_word_text(source_word):
            return source_word

    if normalized_target == "en":
        translated_word = _normalize_word_candidate(translated_text)
        if translated_word and is_single_word_text(translated_word):
            return translated_word
        return ""

    try:
        english_hint = translate(translated_text, normalized_target, "en").result
    except Exception:
        return ""

    english_word = _normalize_word_candidate(english_hint)
    if english_word and is_single_word_text(english_word):
        return english_word

    return ""


def quick_convert(text: str, source: str, target: str) -> dict:
    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "kind": "text",
            "result": "",
            "engine": "none",
            "mode": "empty",
            "fallback_used": False,
            "word_data": None,
        }

    resolved_source = detect_language(cleaned) if source == "auto" else source
    normalized_source = normalize_lang(resolved_source)
    normalized_target = normalize_lang(target)

    if is_single_word_text(cleaned):
        translated = _choose_single_word_translation(cleaned, resolved_source, target)
    else:
        translated = translate(cleaned, source, target)

    use_english_metadata = normalized_source == "en" or normalized_target == "en"
    word_data: dict[str, Any] | None = None

    if use_english_metadata:
        english_anchor_word = _resolve_english_anchor_word(
            cleaned,
            translated.result,
            resolved_source,
            target,
        )
        if english_anchor_word:
            word_data = _build_word_data(english_anchor_word, "en")
    else:
        word_data = _build_word_data(translated.result, normalized_target)

    if not word_data and not use_english_metadata:
        try:
            english_hint = translate(translated.result, target, "en").result
            if is_single_word_text(_normalize_word_candidate(english_hint)):
                word_data = _build_word_data(english_hint, "en")
                if word_data and target != "en":
                    word_data["synonyms"] = _translate_terms(
                        word_data.get("synonyms") or [], "en", target, limit=6
                    )
                    word_data["related"] = _translate_terms(
                        word_data.get("related") or [], "en", target, limit=6
                    )
                    word_data["sounds_like"] = _translate_terms(
                        word_data.get("sounds_like") or [], "en", target, limit=6
                    )
                    word_data["input"] = _normalize_word_candidate(translated.result)
        except Exception:
            pass

    return {
        "kind": "word" if word_data else "text",
        "result": translated.result,
        "engine": translated.engine,
        "mode": f"{translated.mode}+word-enriched" if word_data else translated.mode,
        "fallback_used": translated.engine != "argos",
        "word_data": word_data,
    }


__all__ = [
    "TranslationResult",
    "detect_language",
    "lookup_dictionary",
    "normalize_lang",
    "quick_convert",
    "translate",
]
