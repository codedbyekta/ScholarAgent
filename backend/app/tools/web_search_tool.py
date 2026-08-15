"""
TOOL 3 of 4: Live web search, used to fact-check / freshness-check claims
pulled from papers. Tavily is used if a key is set (better quality);
otherwise falls back to DuckDuckGo (no key required at all) - a
deliberate graceful-degradation design so the project runs even with
zero paid API keys.
"""

import logging

import httpx
from duckduckgo_search import DDGS

from app.core.config import settings

logger = logging.getLogger(__name__)


def _search_tavily(query: str, max_results: int = 5) -> list[dict]:
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": settings.tavily_api_key, "query": query, "max_results": max_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {"title": r.get("title", ""), "snippet": r.get("content", ""), "url": r.get("url", "")}
            for r in data.get("results", [])
        ]
    except httpx.HTTPError as exc:
        logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", exc)
        return []


def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")}
            for r in results
        ]
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return []


def web_search(query: str, max_results: int = 5) -> list[dict]:
    if settings.tavily_api_key:
        results = _search_tavily(query, max_results)
        if results:
            return results
    results = _search_duckduckgo(query, max_results)
    logger.info("web_search('%s') -> %d results", query, len(results))
    return results
