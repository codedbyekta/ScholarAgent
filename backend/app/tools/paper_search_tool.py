"""
TOOL 1 of 4: Academic paper search (arXiv + Semantic Scholar).
Finds real, current papers instead of relying on the LLM's own memory
of "papers that exist" (which risks being outdated or hallucinated).
Both APIs are free, need no key. This is also the tool the evaluation
engine measures Retrieval Precision@K and Retrieval Success Rate against,
since arXiv/Semantic Scholar results are reproducible for well-known
seminal queries.
"""
import logging
import time
import xml.etree.ElementTree as ET
import httpx

logger = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"


def _search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results, "sortBy": "relevance"}
    try:
        resp = httpx.get(ARXIV_API, params=params, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("arXiv search failed: %s", exc)
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns).strip()
        summary = entry.findtext("atom:summary", default="", namespaces=ns).strip()
        link = entry.findtext("atom:id", default="", namespaces=ns).strip()
        published = entry.findtext("atom:published", default="", namespaces=ns)[:10]
        authors = [a.findtext("atom:name", default="", namespaces=ns) for a in entry.findall("atom:author", ns)]
        papers.append(
            {
                "source": "arXiv",
                "title": title,
                "abstract": summary[:600],
                "url": link,
                "published": published,
                "authors": authors[:4],
            }
        )
    return papers


def _search_semantic_scholar(query: str, max_results: int = 5, retries: int = 2) -> list[dict]:
    params = {"query": query, "limit": max_results, "fields": "title,abstract,url,year,authors,citationCount"}
    for attempt in range(retries + 1):
        try:
            resp = httpx.get(SEMANTIC_SCHOLAR_API, params=params, timeout=15, follow_redirects=True)
            if resp.status_code == 429:
                wait = 2 * (attempt + 1)
                logger.warning("Semantic Scholar rate limited, retrying in %ss", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except httpx.HTTPError as exc:
            logger.warning("Semantic Scholar search failed: %s", exc)
            return []
    else:
        logger.warning("Semantic Scholar rate limited after retries, giving up.")
        return []

    papers = []
    for item in data.get("data", []):
        papers.append(
            {
                "source": "Semantic Scholar",
                "title": item.get("title", ""),
                "abstract": (item.get("abstract") or "")[:600],
                "url": item.get("url", ""),
                "published": str(item.get("year", "")),
                "authors": [a.get("name") for a in (item.get("authors") or [])][:4],
                "citation_count": item.get("citationCount", 0),
            }
        )
    return papers


def search_papers(query: str, max_results: int = 5) -> list[dict]:
    """Search arXiv and Semantic Scholar and merge/dedupe by title."""
    combined = _search_arxiv(query, max_results) + _search_semantic_scholar(query, max_results)
    seen = set()
    deduped = []
    for p in combined:
        key = p["title"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(p)
    logger.info("search_papers('%s') -> %d results", query, len(deduped))
    return deduped