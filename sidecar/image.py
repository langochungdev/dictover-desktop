from __future__ import annotations

from typing import Any

try:
    from .engines import HTTP_TIMEOUT, SESSION
except ImportError:
    from engines import HTTP_TIMEOUT, SESSION


IMAGE_TIMEOUT = min(HTTP_TIMEOUT, 8)
MAX_PAGE_SIZE = 24


def _normalize_query(value: str) -> str:
    compact = " ".join(str(value or "").split())
    if not compact:
        return ""
    return " ".join(compact.split(" ")[:8])[:80].strip()


def _normalize_page(value: int) -> int:
    if value < 1:
        return 1
    return value


def _normalize_page_size(value: int) -> int:
    if value < 1:
        return 12
    return min(value, MAX_PAGE_SIZE)


def _to_image_option(page: dict[str, Any]) -> dict[str, str] | None:
    title = str(page.get("title") or "").strip()
    thumbnail = page.get("thumbnail") or {}
    src = str(thumbnail.get("source") or "").strip()
    if not src:
        return None
    fullurl = str(page.get("fullurl") or "").strip()
    pageid = page.get("pageid")
    page_url = fullurl or (
        f"https://en.wikipedia.org/?curid={pageid}" if pageid is not None else src
    )
    return {
        "src": src,
        "source": "Wikipedia",
        "title": title or "Image",
        "page_url": page_url,
    }


def _search_wikipedia(query: str, page: int, page_size: int) -> dict[str, Any]:
    offset = (page - 1) * page_size
    response = SESSION.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 0,
            "gsrlimit": page_size,
            "gsroffset": offset,
            "prop": "pageimages|info",
            "inprop": "url",
            "pithumbsize": 640,
            "format": "json",
        },
        timeout=IMAGE_TIMEOUT,
    )

    if not response.ok:
        return {"options": [], "has_more": False, "next_page": None}

    payload = response.json() if response.content else {}
    pages = (
        ((payload.get("query") or {}).get("pages") or {})
        if isinstance(payload, dict)
        else {}
    )
    ordered = sorted(
        [item for item in pages.values() if isinstance(item, dict)],
        key=lambda item: int(item.get("index") or 0),
    )

    options: list[dict[str, str]] = []
    for item in ordered:
        option = _to_image_option(item)
        if option:
            options.append(option)

    continuation = payload.get("continue") if isinstance(payload, dict) else None
    has_more = bool(
        continuation
        and isinstance(continuation, dict)
        and continuation.get("gsroffset") is not None
    )
    next_page = page + 1 if has_more else None
    return {"options": options, "has_more": has_more, "next_page": next_page}


def _fallback_duckduckgo(query: str) -> list[dict[str, str]]:
    response = SESSION.get(
        "https://api.duckduckgo.com/",
        params={
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        },
        timeout=IMAGE_TIMEOUT,
    )
    if not response.ok:
        return []

    payload = response.json() if response.content else {}
    if not isinstance(payload, dict):
        return []

    image_url = str(payload.get("Image") or "").strip()
    if not image_url:
        return []

    heading = str(payload.get("Heading") or query or "Image").strip()
    abstract_url = str(payload.get("AbstractURL") or "").strip()
    page_url = abstract_url or image_url
    return [
        {
            "src": image_url,
            "source": "DuckDuckGo",
            "title": heading,
            "page_url": page_url,
        }
    ]


def search_images(query: str, page: int = 1, page_size: int = 12) -> dict[str, Any]:
    normalized_query = _normalize_query(query)
    normalized_page = _normalize_page(page)
    normalized_page_size = _normalize_page_size(page_size)

    if not normalized_query:
        return {
            "query": "",
            "page": normalized_page,
            "page_size": normalized_page_size,
            "options": [],
            "next_page": None,
            "has_more": False,
            "error": "empty-query",
        }

    try:
        wikipedia = _search_wikipedia(
            normalized_query,
            normalized_page,
            normalized_page_size,
        )
        options = wikipedia.get("options") or []
        if not options and normalized_page == 1:
            options = _fallback_duckduckgo(normalized_query)

        return {
            "query": normalized_query,
            "page": normalized_page,
            "page_size": normalized_page_size,
            "options": options,
            "next_page": wikipedia.get("next_page"),
            "has_more": bool(wikipedia.get("has_more")),
            "error": "",
        }
    except Exception as exc:
        return {
            "query": normalized_query,
            "page": normalized_page,
            "page_size": normalized_page_size,
            "options": [],
            "next_page": None,
            "has_more": False,
            "error": str(exc),
        }
