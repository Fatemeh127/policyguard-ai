# app/retrieval/filter.py

"""Filter and rerank retrieved chunks before sending to LLM."""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def deduplicate(
    results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Remove duplicate chunks by text.
    Keeps the highest-score version of each duplicate.
    """
    best_by_text = {}

    for r in results:
        text = r.get("text")
        if not text:
            continue

        score = r.get("score") or 0.0

        if text not in best_by_text or score > (best_by_text[text].get("score") or 0.0):
            best_by_text[text] = r

    deduped = list(best_by_text.values())

    logger.debug("Deduplicated %d → %d chunks", len(results), len(deduped))

    return deduped


def filter_by_score(
    results: List[Dict[str, Any]],
    min_score: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Drop chunks below relevance threshold.
    """
    filtered = [
        r for r in results
        if (r.get("score") or 0.0) >= min_score
    ]

    logger.debug(
        "Score filter (min=%.2f): %d → %d",
        min_score, len(results), len(filtered)
    )

    return filtered


def filter_by_document(
    results: List[Dict[str, Any]],
    document_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Keep only chunks from a specific document.
    If document_id is None, returns unchanged list.
    """
    if document_id is None:
        return results

    filtered = [
        r for r in results
        if r.get("document_id") == document_id
    ]

    logger.debug(
        "Document filter (%s): %d → %d",
        document_id, len(results), len(filtered)
    )

    return filtered


def apply_filters(
    results: List[Dict[str, Any]],
    *,
    min_score: float = 0.5,
    document_id: Optional[str] = None,
    dedup: bool = True
) -> List[Dict[str, Any]]:
    """
    Full filtering pipeline:
    1. deduplicate
    2. filter by document (optional)
    3. filter by score
    4. sort by score (descending)
    """

    if not results:
        return []

    logger.debug("Starting filtering pipeline with %d chunks", len(results))

    # 1. Deduplication
    if dedup:
        results = deduplicate(results)

    # 2. Document filter
    results = filter_by_document(results, document_id)

    # 3. Score filter
    results = filter_by_score(results, min_score)

    # 4. Sorting (VERY important for LLM quality)
    results = sorted(
        results,
        key=lambda x: x.get("score") or 0.0,
        reverse=True
    )

    logger.debug("Final filtered chunks: %d", len(results))

    return results