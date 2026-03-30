from __future__ import annotations

import datetime as dt
import os
import re
from typing import Any

from common import dump_json, http_get_json


QUERIES = ["cat", "xin chào", "こんにちは", "bonjour"]


def token_score(query: str, title: str) -> int:
    q_tokens = [t for t in re.split(r"\W+", query.lower()) if t]
    t_tokens = [t for t in re.split(r"\W+", title.lower()) if t]
    if not q_tokens:
        return 0
    overlap = len(set(q_tokens) & set(t_tokens))
    exact = 3 if query.lower().strip() == title.lower().strip() else 0
    prefix = 1 if title.lower().startswith(query.lower().strip()) else 0
    return exact + prefix + overlap


def duckduckgo_probe(query: str) -> dict[str, Any]:
    res = http_get_json(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
    )
    image_url = ""
    related_count = 0
    if isinstance(res.json_data, dict):
        image_url = res.json_data.get("Image") or ""
        related = res.json_data.get("RelatedTopics") or []
        if isinstance(related, list):
            related_count = len(related)
    return {
        "status_code": res.status_code,
        "latency_ms": res.latency_ms,
        "ok": res.ok,
        "image_url": image_url,
        "related_topics_count": related_count,
        "error": res.error,
    }


def wikipedia_search_probe(query: str) -> dict[str, Any]:
    res = http_get_json(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "utf8": 1,
            "format": "json",
        },
    )
    rows = []
    if isinstance(res.json_data, dict):
        for item in ((res.json_data.get("query") or {}).get("search") or [])[:8]:
            if isinstance(item, dict):
                title = item.get("title") or ""
                rows.append({"title": title, "score": token_score(query, title)})
    ranked = sorted(rows, key=lambda x: x["score"], reverse=True)
    return {
        "status_code": res.status_code,
        "latency_ms": res.latency_ms,
        "ok": res.ok,
        "results": ranked,
        "error": res.error,
    }


def wikipedia_exact_title_probe(query: str) -> dict[str, Any]:
    res = http_get_json(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": query,
            "prop": "pageimages|info",
            "inprop": "url",
            "pithumbsize": 480,
            "format": "json",
        },
    )
    exact = None
    if isinstance(res.json_data, dict):
        pages = ((res.json_data.get("query") or {}).get("pages") or {})
        if isinstance(pages, dict):
            for page in pages.values():
                if isinstance(page, dict) and page.get("pageid"):
                    exact = {
                        "title": page.get("title"),
                        "pageid": page.get("pageid"),
                        "fullurl": page.get("fullurl"),
                        "thumbnail": ((page.get("thumbnail") or {}).get("source")),
                    }
                    break
    return {
        "status_code": res.status_code,
        "latency_ms": res.latency_ms,
        "ok": res.ok,
        "result": exact,
        "error": res.error,
    }


def google_cse_probe(query: str) -> dict[str, Any]:
    key = os.getenv("GOOGLE_CSE_KEY", "")
    cx = os.getenv("GOOGLE_CSE_CX", "")
    if not key or not cx:
        return {"enabled": False, "reason": "GOOGLE_CSE_KEY or GOOGLE_CSE_CX missing"}
    res = http_get_json(
        "https://www.googleapis.com/customsearch/v1",
        params={"key": key, "cx": cx, "q": query, "searchType": "image", "num": 5},
    )
    images = []
    if isinstance(res.json_data, dict):
        for item in (res.json_data.get("items") or [])[:5]:
            if isinstance(item, dict):
                images.append(item.get("link"))
    return {
        "enabled": True,
        "status_code": res.status_code,
        "latency_ms": res.latency_ms,
        "ok": res.ok,
        "images": images,
        "error": res.error,
    }


def ui_logic_probe() -> dict[str, Any]:
    ttl_seconds = 8 * 60
    cached_at = 1000
    checks = [
        {"at": 1200, "cache_hit": (1200 - cached_at) <= ttl_seconds},
        {"at": 1600, "cache_hit": (1600 - cached_at) <= ttl_seconds},
    ]
    threshold = 260
    scroll = [
        {"distance_to_bottom": 500, "load_more": 500 <= threshold},
        {"distance_to_bottom": 260, "load_more": 260 <= threshold},
        {"distance_to_bottom": 120, "load_more": 120 <= threshold},
    ]
    return {"ttl_seconds": ttl_seconds, "cache_checks": checks, "infinite_scroll_checks": scroll}


def main() -> None:
    rows = []
    for query in QUERIES:
        rows.append(
            {
                "query": query,
                "duckduckgo": duckduckgo_probe(query),
                "google_cse": google_cse_probe(query),
                "wikipedia_search": wikipedia_search_probe(query),
                "wikipedia_exact": wikipedia_exact_title_probe(query),
            }
        )
    data = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "ui_logic": ui_logic_probe(),
        "cases": rows,
    }
    dump_json(data)


if __name__ == "__main__":
    main()
