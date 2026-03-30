from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests


DEFAULT_HEADERS = {
    "User-Agent": "DictOver-Probe/1.0 (+https://example.local)",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(DEFAULT_HEADERS)


LANG_ALIASES = {
    "zh-CN": "zh",
    "zh": "zh",
}


@dataclass
class HttpResult:
    ok: bool
    status_code: int
    latency_ms: float
    text: str
    json_data: Any
    error: str | None = None


def normalize_lang(lang: str) -> str:
    return LANG_ALIASES.get(lang, lang)


def http_get_json(url: str, params: dict[str, Any] | None = None, timeout: int = 12) -> HttpResult:
    start = time.perf_counter()
    try:
        resp = SESSION.get(url, params=params, timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000.0
        text = resp.text or ""
        parsed = None
        try:
            parsed = resp.json()
        except Exception:
            parsed = None
        return HttpResult(
            ok=resp.ok,
            status_code=resp.status_code,
            latency_ms=round(latency_ms, 2),
            text=text,
            json_data=parsed,
            error=None,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return HttpResult(
            ok=False,
            status_code=0,
            latency_ms=round(latency_ms, 2),
            text="",
            json_data=None,
            error=str(exc),
        )


def http_get_text(url: str, params: dict[str, Any] | None = None, timeout: int = 12) -> HttpResult:
    start = time.perf_counter()
    try:
        resp = SESSION.get(url, params=params, timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000.0
        return HttpResult(
            ok=resp.ok,
            status_code=resp.status_code,
            latency_ms=round(latency_ms, 2),
            text=resp.text or "",
            json_data=None,
            error=None,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return HttpResult(
            ok=False,
            status_code=0,
            latency_ms=round(latency_ms, 2),
            text="",
            json_data=None,
            error=str(exc),
        )


def probe_binary_url(url: str, timeout: int = 12) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        headers = {"Range": "bytes=0-1024"}
        all_headers = dict(DEFAULT_HEADERS)
        all_headers.update(headers)
        resp = SESSION.get(url, timeout=timeout, headers=all_headers, stream=True)
        latency_ms = (time.perf_counter() - start) * 1000.0
        content_type = resp.headers.get("Content-Type", "")
        return {
            "ok": resp.ok,
            "status_code": resp.status_code,
            "latency_ms": round(latency_ms, 2),
            "content_type": content_type,
            "final_url": resp.url,
            "error": None,
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return {
            "ok": False,
            "status_code": 0,
            "latency_ms": round(latency_ms, 2),
            "content_type": "",
            "final_url": url,
            "error": str(exc),
        }


def safe_quote(text: str) -> str:
    return quote(text, safe="")


def dump_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
