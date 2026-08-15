"""
Wrapper around ChromaDB running in local persistent mode (writes to a
folder on disk, no separate server process - this is what lets the whole
project run without Docker).

Same job as before: store embedded PDF chunks, and semantically search
them back. Embeddings themselves come from Gemini (app/core/llm_client),
not from Chroma's own default embedding function - we pass vectors in
directly so both storage and retrieval use the exact same embedding
model deliberately.
"""

import logging
import uuid

import chromadb

from app.core.config import settings
from app.core.llm_client import embed_texts, embed_text

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def get_collection():
    return get_client().get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(session_id: str, doc_name: str, chunks: list[str]) -> int:
    if not chunks:
        return 0

    vectors = embed_texts(chunks, task_type="RETRIEVAL_DOCUMENT")
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"session_id": session_id, "doc_name": doc_name} for _ in chunks]

    get_collection().add(ids=ids, embeddings=vectors, documents=chunks, metadatas=metadatas)
    logger.info("Upserted %d chunks from '%s' for session %s", len(chunks), doc_name, session_id)
    return len(chunks)


def search(session_id: str, query: str, top_k: int = 5) -> list[dict]:
    query_vector = embed_text(query, task_type="RETRIEVAL_QUERY")
    results = get_collection().query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where={"session_id": session_id},
    )

    if not results["ids"] or not results["ids"][0]:
        return []

    out = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        out.append({"text": doc, "doc_name": meta.get("doc_name", "unknown"), "score": 1 - dist})
    return out


def session_has_documents(session_id: str) -> bool:
    results = get_collection().get(where={"session_id": session_id}, limit=1)
    return len(results.get("ids", [])) > 0
