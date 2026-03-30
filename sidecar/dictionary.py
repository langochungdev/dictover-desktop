from __future__ import annotations

from typing import Any
from urllib.parse import quote

try:
    from .engines import HTTP_TIMEOUT, SESSION, normalize_lang, translate
except ImportError:
    from engines import HTTP_TIMEOUT, SESSION, normalize_lang, translate


def _scan_audio_url(node: Any) -> str | None:
    if isinstance(node, dict):
        for value in node.values():
            found = _scan_audio_url(value)
            if found:
                return found
        return None
    if isinstance(node, list):
        for value in node:
            found = _scan_audio_url(value)
            if found:
                return found
        return None
    if isinstance(node, str):
        lower = node.lower()
        if node.startswith("http") and (".mp3" in lower or ".ogg" in lower):
            return node
    return None


def _parse_wiktionary(payload: Any) -> tuple[str | None, list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                entries.extend(x for x in value if isinstance(x, dict))
    phonetic: str | None = None
    meanings: list[dict[str, Any]] = []
    for entry in entries:
        if not phonetic and isinstance(entry.get("pronunciations"), list):
            pron = entry.get("pronunciations") or []
            if pron and isinstance(pron[0], dict):
                raw = pron[0].get("ipa")
                if isinstance(raw, str) and raw.strip():
                    phonetic = raw
        definitions = entry.get("definitions")
        if not isinstance(definitions, list):
            continue
        bucket: list[str] = []
        example: str | None = None
        for item in definitions:
            if isinstance(item, dict):
                definition = item.get("definition")
                if isinstance(definition, str) and definition.strip():
                    bucket.append(definition.strip())
                if not example:
                    sample = item.get("example")
                    if isinstance(sample, str) and sample.strip():
                        example = sample.strip()
        if bucket:
            meanings.append(
                {
                    "part_of_speech": str(entry.get("partOfSpeech") or "meaning"),
                    "definitions": bucket,
                    "example": example,
                }
            )
    return phonetic, meanings


def _lookup_english(word: str) -> dict[str, Any]:
    response = SESSION.get(
        f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word, safe='')}",
        timeout=HTTP_TIMEOUT,
    )
    payload = response.json() if response.ok else []
    phonetic = None
    audio = None
    meanings: list[dict[str, Any]] = []
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        item = payload[0]
        raw_phonetic = item.get("phonetic")
        if isinstance(raw_phonetic, str) and raw_phonetic.strip():
            phonetic = raw_phonetic
        if isinstance(item.get("phonetics"), list):
            for p in item.get("phonetics") or []:
                if (
                    isinstance(p, dict)
                    and isinstance(p.get("audio"), str)
                    and p.get("audio")
                ):
                    audio = p.get("audio")
                    break
        for meaning in item.get("meanings") or []:
            if isinstance(meaning, dict):
                defs = []
                example = None
                for d in meaning.get("definitions") or []:
                    if isinstance(d, dict):
                        text = d.get("definition")
                        if isinstance(text, str) and text.strip():
                            defs.append(text.strip())
                        if not example:
                            sample = d.get("example")
                            if isinstance(sample, str) and sample.strip():
                                example = sample.strip()
                if defs:
                    meanings.append(
                        {
                            "part_of_speech": str(
                                meaning.get("partOfSpeech") or "meaning"
                            ),
                            "definitions": defs,
                            "example": example,
                        }
                    )
    return {
        "word": word,
        "phonetic": phonetic,
        "audio_url": audio,
        "meanings": meanings,
        "provider": "dictionaryapi.dev",
        "fallback_used": False,
    }


def lookup_dictionary(word: str, source_lang: str) -> dict[str, Any]:
    if source_lang == "en":
        return _lookup_english(word)

    lang = normalize_lang(source_lang)
    urls = [
        f"https://{lang}.wiktionary.org/api/rest_v1/page/definition/{quote(word, safe='')}",
        f"https://en.wiktionary.org/api/rest_v1/page/definition/{quote(word, safe='')}",
    ]
    for index, url in enumerate(urls):
        response = SESSION.get(url, timeout=HTTP_TIMEOUT)
        if not response.ok:
            continue
        payload = response.json()
        phonetic, meanings = _parse_wiktionary(payload)
        if meanings:
            return {
                "word": word,
                "phonetic": phonetic,
                "audio_url": _scan_audio_url(payload),
                "meanings": meanings,
                "provider": "wiktionary-rest",
                "fallback_used": index == 1,
            }

    translated = translate(word, source_lang, "en")
    return {
        "word": word,
        "phonetic": None,
        "audio_url": None,
        "meanings": [
            {
                "part_of_speech": "fallback",
                "definitions": [translated.result],
                "example": None,
            }
        ],
        "provider": "auto_lookup_fallback",
        "fallback_used": True,
    }
