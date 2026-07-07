"""Web search.

Primary: Google Search grounding via the Gemini API (actual Google results,
reliable, free on the Gemini tier) when a Gemini key is available.
Fallback: DuckDuckGo scraping (no key, but frequently rate-limited).
"""
from __future__ import annotations

from typing import Any

import httpx

from app.utils.logging import get_logger

log = get_logger(__name__)


def _gemini_grounded_search(query: str, api_key: str, model: str) -> list[dict[str, Any]] | None:
    """Use Gemini's google_search grounding. Returns [{title,url,snippet}] or None."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": query}]}], "tools": [{"google_search": {}}]}
    r = httpx.post(url, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    cand = (data.get("candidates") or [{}])[0]
    parts = cand.get("content", {}).get("parts", [])
    answer = " ".join(p.get("text", "") for p in parts if p.get("text")).strip()
    if not answer:
        return None
    gm = cand.get("groundingMetadata", {}) or {}
    sources: list[dict[str, Any]] = []
    for chunk in (gm.get("groundingChunks") or [])[:5]:
        web = chunk.get("web", {})
        if web.get("uri"):
            sources.append({"title": web.get("title", ""), "url": web["uri"], "snippet": ""})
    top = sources[0]["url"] if sources else ""
    return [{"title": "Google answer", "url": top, "snippet": answer}, *sources]


def _duckduckgo_search(query: str, max_results: int) -> list[dict[str, Any]]:
    try:
        from ddgs import DDGS
    except ImportError:
        try:  # older package name
            from duckduckgo_search import DDGS  # type: ignore[no-redef]
        except ImportError:
            log.warning("no DuckDuckGo search package installed")
            return []
    # "auto" often returns nothing (scrape throttling); html/lite are steadier
    for backend in ("html", "lite", "auto"):
        try:
            with DDGS() as ddgs:
                try:
                    raw = list(ddgs.text(query, max_results=max_results, backend=backend))
                except TypeError:
                    raw = list(ddgs.text(query, max_results=max_results))
            if raw:
                return [
                    {"title": r.get("title", ""), "url": r.get("href", r.get("url", "")),
                     "snippet": r.get("body", "")}
                    for r in raw
                ]
        except Exception as e:  # noqa: BLE001 — try next backend
            log.warning("ddg backend %s failed: %s: %s", backend, type(e).__name__, e)
    return []


def web_search(
    query: str,
    max_results: int = 6,
    gemini_api_key: str = "",
    gemini_model: str = "gemini-2.5-flash",
) -> list[dict[str, Any]]:
    """Return [{title, url, snippet}]; empty list on total failure."""
    if gemini_api_key:
        try:
            res = _gemini_grounded_search(query, gemini_api_key, gemini_model)
            if res:
                return res
        except Exception as e:  # noqa: BLE001 — fall back to DDG
            log.warning("gemini grounded search failed: %s: %s", type(e).__name__, e)

    res = _duckduckgo_search(query, max_results)
    if not res:
        log.warning("web search returned no results for %r", query)
    return res
