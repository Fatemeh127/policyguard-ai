"""Retrieve relevant chunks from the vector store for a given query."""

import logging
from typing import Any

from app.core.config import settings
from app.retrieval.filter import apply_filters
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _search_vector_store(
    query: str,
    vector_store: VectorStore,
    role: str,
    top_k: int,
) -> list[dict[str, Any]]:
    """Safely search the vector store."""

    try:
        results = vector_store.search(
            query=query,
            role=role,
            limit=top_k,
        )
    except Exception:
        logger.exception(
            "Vector search failed | role=%s | top_k=%d",
            role,
            top_k,
        )
        return []

    if not isinstance(results, list):
        logger.warning(
            "Vector store returned invalid result type: %s",
            type(results),
        )
        return []

    return results


def _get_filtered_results(
    query: str,
    vector_store: VectorStore,
    role: str,
    top_k: int,
    min_score: float,
) -> list[dict[str, Any]]:
    """
    Search, filter, deduplicate, sort, and retry once if no useful chunks remain.
    """

    results = _search_vector_store(
        query=query,
        vector_store=vector_store,
        role=role,
        top_k=top_k,
    )

    filtered = apply_filters(
        results,
        min_score=min_score,
        dedup=True,
        limit=top_k,
    )

    if filtered:
        return filtered

    logger.warning(
        "No chunks after filtering. Retrying with expanded top_k | role=%s | top_k=%d",
        role,
        top_k * 2,
    )

    retry_results = _search_vector_store(
        query=query,
        vector_store=vector_store,
        role=role,
        top_k=top_k * 2,
    )

    return apply_filters(
        retry_results,
        min_score=min_score,
        dedup=True,
        limit=top_k,
    )


def _clean_metadata_result(result: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize one vector result into a clean RAG chunk."""

    text = result.get("text")

    if not isinstance(text, str) or not text.strip():
        return None

    return {
        "text": text.strip(),
        "score": result.get("score"),
        "document_id": result.get("document_id"),
        "chunk_id": result.get("chunk_id"),
        "role": result.get("role"),
    }


def retrieve_chunks_with_metadata(
    query: str,
    vector_store: VectorStore,
    role: str = "employee",
    top_k: int = 5,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant chunks with metadata for RAG answer generation.
    """

    if not query.strip():
        logger.warning("Empty query received for retrieval.")
        return []

    min_score = settings.min_retrieval_score if min_score is None else min_score

    filtered_results = _get_filtered_results(
        query=query,
        vector_store=vector_store,
        role=role,
        top_k=top_k,
        min_score=min_score,
    )

    cleaned = [
        cleaned_result
        for result in filtered_results
        if (cleaned_result := _clean_metadata_result(result)) is not None
    ]

    logger.debug(
        "Final metadata chunks prepared | count=%d | role=%s",
        len(cleaned),
        role,
    )

    return cleaned


def retrieve_chunks(
    query: str,
    vector_store: VectorStore,
    role: str = "employee",
    top_k: int = 5,
    min_score: float | None = None,
) -> list[str]:
    """
    Retrieve clean text chunks only, ready to be used as LLM context.
    """

    chunks_with_metadata = retrieve_chunks_with_metadata(
        query=query,
        vector_store=vector_store,
        role=role,
        top_k=top_k,
        min_score=min_score,
    )

    chunks = [chunk["text"] for chunk in chunks_with_metadata]

    logger.debug("Final text chunks prepared | count=%d", len(chunks))

    return chunks
