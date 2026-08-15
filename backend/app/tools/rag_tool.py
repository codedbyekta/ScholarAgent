"""
TOOL 2 of 4: Semantic RAG retrieval over the user's own uploaded PDFs
(stored in Chroma). Different from Tool 1: this searches documents the
USER personally uploaded, not the open web.
"""

import logging

from app.db.chroma_store import search as chroma_search

logger = logging.getLogger(__name__)


def rag_search(session_id: str, query: str, top_k: int = 5) -> list[dict]:
    results = chroma_search(session_id=session_id, query=query, top_k=top_k)
    logger.info("rag_search('%s...', session=%s) -> %d chunks", query[:40], session_id, len(results))
    return results
