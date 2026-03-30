from __future__ import annotations

import datetime as dt
import re
from typing import Any

from common import dump_json, http_get_json, normalize_lang, probe_binary_url, safe_quote


CASES = [
    ("hello", "en", ["phonetic", "meanings", "audio_url"]),
    ("xin chào", "vi", ["phonetic", "meanings"]),
    ("こんにちは", "ja", ["meanings"]),
    ("안녕하세요", "ko", ["meanings"]),
    ("привет", "ru", ["meanings"]),
    ("你好", "zh-CN", ["meanings"]),
    ("hallo", "de", ["meanings"]),
    ("bonjour", "fr", ["meanings"]),
    ("hei", "fi", ["meanings"]),
]


AUDIO_TEMPLATE_RE = re.compile(r"\{\{audio\|[^|]*\|([^|}]+)", re.IGNORECASE)
FILE_RE = re.compile(r"\[\[(?:File|Datei|Fichier|T\u1eadp tin):([^|\]]+\.(?:ogg|oga|mp3|wav))", re.IGNORECASE)


def _scan_audio_urls(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        for sub in value.values():
            _scan_audio_urls(sub, out)
    elif isinstance(value, list):
        for sub in value:
            _scan_audio_urls(sub, out)
    elif isinstance(value, str):
        low = value.lower()
        if value.startswith("http") and (".ogg" in low or ".mp3" in low or "audio" in low):
            out.append(value)


def parse_dictionaryapi(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list) or not payload:
        return {"phonetic": False, "meanings": False, "audio_url": None}
    entry = payload[0] if isinstance(payload[0], dict) else {}
    phonetic = bool(entry.get("phonetic"))
    meanings = bool(entry.get("meanings"))
    audio_url = None
    for p in entry.get("phonetics", []) if isinstance(entry.get("phonetics"), list) else []:
        if isinstance(p, dict) and p.get("audio"):
            audio_url = p["audio"]
            break
    return {"phonetic": phonetic, "meanings": meanings, "audio_url": audio_url}


def parse_wiktionary_rest(payload: Any) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                entries.extend(x for x in v if isinstance(x, dict))
    meanings = False
    phonetic = False
    audio_urls: list[str] = []
    for entry in entries:
        defs = entry.get("definitions")
        if isinstance(defs, list) and defs:
            meanings = True
        if isinstance(entry.get("senses"), list) and entry.get("senses"):
            meanings = True
        if entry.get("pronunciation") or entry.get("pronunciations"):
            phonetic = True
        _scan_audio_urls(entry, audio_urls)
    return {
        "phonetic": phonetic,
        "meanings": meanings,
        "audio_url": audio_urls[0] if audio_urls else None,
    }


def lookup_wiktionary_with_fallback(word: str, source_lang: str) -> dict[str, Any]:
    domain = normalize_lang(source_lang)
    urls = [
        (f"{domain}.wiktionary.org", f"https://{domain}.wiktionary.org/api/rest_v1/page/definition/{safe_quote(word)}"),
        ("en.wiktionary.org", f"https://en.wiktionary.org/api/rest_v1/page/definition/{safe_quote(word)}"),
    ]
    attempts = []
    selected = None
    last = None
    for host, url in urls:
        res = http_get_json(url)
        parsed = parse_wiktionary_rest(res.json_data)
        last = (host, res, parsed)
        attempts.append(
            {
                "host": host,
                "status_code": res.status_code,
                "latency_ms": res.latency_ms,
                "ok": res.ok,
                "fields": {"phonetic": bool(parsed.get("phonetic")), "meanings": bool(parsed.get("meanings"))},
                "error": res.error,
            }
        )
        if res.ok and parsed.get("meanings") and selected is None:
            selected = (host, res, parsed)
    if selected is None:
        host, res, parsed = last
        return {"host": host, "res": res, "parsed": parsed, "attempts": attempts}
    host, res, parsed = selected
    return {"host": host, "res": res, "parsed": parsed, "attempts": attempts}


def probe_wiktionary_audio_template(word: str, lang: str) -> dict[str, Any]:
    domain = normalize_lang(lang)
    url = f"https://{domain}.wiktionary.org/w/api.php"
    params = {
        "action": "query",
        "titles": word,
        "prop": "revisions",
        "rvslots": "main",
        "rvprop": "content",
        "format": "json",
        "formatversion": "2",
    }
    res = http_get_json(url, params=params)
    content = ""
    if isinstance(res.json_data, dict):
        pages = (((res.json_data.get("query") or {}).get("pages")) or [])
        if isinstance(pages, list) and pages and isinstance(pages[0], dict):
            revs = pages[0].get("revisions") or []
            if isinstance(revs, list) and revs and isinstance(revs[0], dict):
                slots = revs[0].get("slots") or {}
                content = ((slots.get("main") or {}).get("content")) or ""
    files = AUDIO_TEMPLATE_RE.findall(content) + FILE_RE.findall(content)
    files = [f.strip() for f in files if f.strip()]
    candidate = None
    probe = None
    if files:
        candidate = f"https://commons.wikimedia.org/wiki/Special:FilePath/{safe_quote(files[0])}"
        probe = probe_binary_url(candidate)
    return {
        "status_code": res.status_code,
        "latency_ms": res.latency_ms,
        "audio_markers": len(files),
        "candidate_audio_url": candidate,
        "candidate_probe": probe,
        "error": res.error,
    }


def fallback_translate_word(word: str, source_lang: str) -> dict[str, Any]:
    url = "https://api.mymemory.translated.net/get"
    params = {"q": word, "langpair": f"{normalize_lang(source_lang)}|en"}
    res = http_get_json(url, params=params)
    translated = ""
    if isinstance(res.json_data, dict):
        translated = ((res.json_data.get("responseData") or {}).get("translatedText")) or ""
    return {
        "status_code": res.status_code,
        "latency_ms": res.latency_ms,
        "translated_text": translated,
        "ok": bool(translated),
        "error": res.error,
    }


def main() -> None:
    rows: list[dict[str, Any]] = []
    for word, source_lang, expected in CASES:
        if source_lang == "en":
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{safe_quote(word)}"
            res = http_get_json(url)
            parsed = parse_dictionaryapi(res.json_data)
            attempts = None
            provider = "dictionaryapi.dev"
        else:
            lookup = lookup_wiktionary_with_fallback(word, source_lang)
            res = lookup["res"]
            parsed = lookup["parsed"]
            attempts = lookup["attempts"]
            provider = f"wiktionary-rest:{lookup['host']}"
        checks = {key: bool(parsed.get(key)) for key in expected}
        fallback_triggered = (not res.ok) or ("meanings" in checks and not checks["meanings"])
        fallback = fallback_translate_word(word, source_lang) if fallback_triggered else None
        action_audio = probe_wiktionary_audio_template(word, source_lang) if source_lang != "en" else None
        rows.append(
            {
                "word": word,
                "source_lang": source_lang,
                "provider": provider,
                "lookup": {
                    "status_code": res.status_code,
                    "latency_ms": res.latency_ms,
                    "ok": res.ok,
                    "error": res.error,
                },
                "lookup_attempts": attempts,
                "fields": checks,
                "audio_url": parsed.get("audio_url"),
                "audio_probe": probe_binary_url(parsed["audio_url"]) if parsed.get("audio_url") else None,
                "action_audio_probe": action_audio,
                "fallback_triggered": fallback_triggered,
                "fallback": fallback,
            }
        )
    success = sum(1 for row in rows if row["lookup"]["ok"])
    data = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "total_cases": len(rows),
        "lookup_success_cases": success,
        "cases": rows,
    }
    dump_json(data)


if __name__ == "__main__":
    main()
