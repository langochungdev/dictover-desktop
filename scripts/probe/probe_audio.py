from __future__ import annotations

import datetime as dt
import shutil
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from common import (
    dump_json,
    http_get_json,
    normalize_lang,
    probe_binary_url,
    safe_quote,
)


SAMPLES = [
    ("hello", "en"),
    ("xin chào", "vi"),
    ("こんにちは", "ja"),
    ("안녕하세요", "ko"),
    ("привет", "ru"),
    ("你好", "zh-CN"),
]


def scan_audio_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for value in payload.values():
            found = scan_audio_url(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = scan_audio_url(value)
            if found:
                return found
    elif isinstance(payload, str):
        low = payload.lower()
        if payload.startswith("http") and (
            ".mp3" in low or ".ogg" in low or "tts" in low
        ):
            return payload
    return None


def lookup_audio_url(word: str, lang: str) -> dict[str, Any]:
    if lang == "en":
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{safe_quote(word)}"
        res = http_get_json(url)
        audio_url = None
        if (
            isinstance(res.json_data, list)
            and res.json_data
            and isinstance(res.json_data[0], dict)
        ):
            for phonetic in res.json_data[0].get("phonetics", []):
                if isinstance(phonetic, dict) and phonetic.get("audio"):
                    audio_url = phonetic["audio"]
                    break
        return {
            "provider": "dictionaryapi.dev",
            "status_code": res.status_code,
            "audio_url": audio_url,
        }
    domain = normalize_lang(lang)
    urls = [
        (
            f"{domain}.wiktionary.org",
            f"https://{domain}.wiktionary.org/api/rest_v1/page/definition/{safe_quote(word)}",
        ),
        (
            "en.wiktionary.org",
            f"https://en.wiktionary.org/api/rest_v1/page/definition/{safe_quote(word)}",
        ),
    ]
    attempts = []
    selected = None
    for host, url in urls:
        res = http_get_json(url)
        audio_url = scan_audio_url(res.json_data)
        attempts.append(
            {
                "host": host,
                "status_code": res.status_code,
                "audio_found": bool(audio_url),
            }
        )
        if res.ok and audio_url and selected is None:
            selected = {
                "provider": f"wiktionary-rest:{host}",
                "status_code": res.status_code,
                "audio_url": audio_url,
            }
    if selected:
        selected["attempts"] = attempts
        return selected
    return {
        "provider": "wiktionary-rest:en.wiktionary.org",
        "status_code": attempts[-1]["status_code"],
        "audio_url": None,
        "attempts": attempts,
    }


def swap_google_tts_variants(url: str) -> list[str]:
    parsed = urlparse(url)
    variants = {url}
    hosts = {"translate.googleapis.com", "translate.google.com"}
    if parsed.netloc in hosts:
        for host in hosts:
            variants.add(urlunparse(parsed._replace(netloc=host)))
    path = parsed.path
    if "gtx" in path or "tw-ob" in path:
        variants.add(urlunparse(parsed._replace(path=path.replace("gtx", "tw-ob"))))
        variants.add(urlunparse(parsed._replace(path=path.replace("tw-ob", "gtx"))))
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "client" in params and params["client"] in {"gtx", "tw-ob"}:
        for value in ["gtx", "tw-ob"]:
            params["client"] = value
            variants.add(urlunparse(parsed._replace(query=urlencode(params))))
    return sorted(v for v in variants if v)


def main() -> None:
    rows = []
    for word, lang in SAMPLES:
        lookup = lookup_audio_url(word, lang)
        audio_url = lookup["audio_url"]
        primary_probe = probe_binary_url(audio_url) if audio_url else None
        retries = []
        if audio_url:
            for variant in swap_google_tts_variants(audio_url):
                if variant == audio_url:
                    continue
                retries.append({"url": variant, "probe": probe_binary_url(variant)})
        retry_success = next((item for item in retries if item["probe"]["ok"]), None)
        chain_result = "speech_synthesis_fallback"
        if primary_probe and primary_probe["ok"]:
            chain_result = "html5_audio_ok"
        elif retry_success:
            chain_result = "google_url_swap_ok"
        elif shutil.which("mpv") or shutil.which("ffplay"):
            chain_result = "native_audio_available"
        rows.append(
            {
                "word": word,
                "source_lang": lang,
                "lookup": lookup,
                "primary_probe": primary_probe,
                "swap_retries": retries,
                "chain_result": chain_result,
            }
        )

    google_tts_sample = "https://translate.googleapis.com/translate_tts?ie=UTF-8&q=hello&tl=en&client=gtx"
    swap_test = []
    for variant in swap_google_tts_variants(google_tts_sample):
        swap_test.append({"url": variant, "probe": probe_binary_url(variant)})

    data = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "fallback_chain": [
            "html5_audio",
            "google_url_swap",
            "native_audio",
            "speech_synthesis",
        ],
        "native_audio": {
            "mpv": bool(shutil.which("mpv")),
            "ffplay": bool(shutil.which("ffplay")),
        },
        "speech_synthesis_probe": {
            "status": "manual-check-required",
            "reason": "Web Speech API needs runtime check inside Tauri WebView2/WebKitGTK",
        },
        "google_swap_regex_probe": swap_test,
        "cases": rows,
    }
    dump_json(data)


if __name__ == "__main__":
    main()
