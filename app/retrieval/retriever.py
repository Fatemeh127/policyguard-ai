"""Retrieve relevant chunks from the vector store for a given query."""

from typing import List, Dict, Any
import logging

from app.retrieval.vector_store import VectorStore
from app.retrieval.filter import apply_filters

logger = logging.getLogger(__name__)


# --- Private helpers ---


def _search_vector_store(
    query: str, vector_store: VectorStore, role: str, top_k: int
) -> List[Dict[str, Any]]:
    """
    Safe wrapper around vector store search.
    Ensures error handling and consistent output.
    """
    try:
        results = vector_store.search(query=query, role=role, limit=top_k)
        if not isinstance(results, list):
            logger.warning("Vector store returned invalid type: %s", type(results))
            return []
        return results

    except Exception as e:
        logger.error("Vector search failed | query=%s | role=%s | error=%s", query, role, str(e))
        return []


def _apply_retrieval_pipeline(
    results: List[Dict[str, Any]], min_score: float
) -> List[Dict[str, Any]]:
    """
    Standard RAG retrieval post-processing:
    1. Deduplicate  — remove duplicate chunks
    2. Filter       — drop weak matches below min_score
    3. Sort         — best results first (critical for LLM quality)
    """
    if not results:
        return []

    results = apply_filters(results, min_score=min_score)
    results = sorted(results, key=lambda x: x.get("score") or 0.0, reverse=True)

    logger.debug("Post-pipeline results count: %d", len(results))
    return results


# --- Public API ---


def retrieve_chunks(
    query: str,
    vector_store: VectorStore,
    role: str = "employee",
    top_k: int = 5,
    min_score: float = 0.5,
) -> List[str]:
    """
    Returns clean text chunks ready for LLM context.

    Use this in:
    - pipeline.py
    - routes/ask.py
    """
    results = _search_vector_store(query, vector_store, role, top_k)
    results = _apply_retrieval_pipeline(results, min_score)

    chunks = [r["text"] for r in results if r.get("text")]

    if not chunks:
        logger.warning(
            "No chunks returned | query=%s | role=%s | min_score=%s", query, role, min_score
        )

    logger.debug("Final chunks for LLM: %d", len(chunks))
    return chunks


def retrieve_chunks_with_metadata(
    query: str, vector_store: VectorStore, role: str, top_k: int = 5, min_score: float = 0.6
) -> List[Dict[str, Any]]:

    results = _search_vector_store(query, vector_store, role, top_k)

    if not results:
        logger.warning("No results found, retrying with higher top_k")
        results = _search_vector_store(query, vector_store, role, top_k * 2)

    filtered = _apply_retrieval_pipeline(results, min_score)

    if not filtered:
        logger.warning("All results filtered out, using raw results")
        filtered = results

    cleaned = [
        {
            "text": r["text"],
            "score": r.get("score"),
            "document_id": r.get("document_id"),
            "chunk_id": r.get("chunk_id"),
            "role": r.get("role"),
        }
        for r in filtered
        if r.get("text")
    ]

    logger.debug("Final metadata chunks: %d", len(cleaned))
    return cleaned
