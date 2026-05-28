"""Filter and rerank retrieved chunks before sending them to the LLM."""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _safe_score(result: dict[str, Any]) -> float:
    """Return a safe numeric score from a retrieval result."""
    try:
        return float(result.get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _normalize_text(text: str) -> str:
    """Normalize text for duplicate detection."""
    return " ".join(text.lower().split())


def deduplicate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Remove duplicate chunks by normalized text.

    Keeps the highest-score version of each duplicate.
    """

    best_by_text: dict[str, dict[str, Any]] = {}

    for result in results:
        text = result.get("text")

        if not isinstance(text, str) or not text.strip():
            continue

        key = _normalize_text(text)
        score = _safe_score(result)

        existing = best_by_text.get(key)

        if existing is None or score > _safe_score(existing):
            best_by_text[key] = result

    deduplicated = list(best_by_text.values())

    logger.debug(
        "Deduplicated chunks | before=%d | after=%d",
        len(results),
        len(deduplicated),
    )

    return deduplicated


def filter_by_score(
    results: list[dict[str, Any]],
    min_score: float,
) -> list[dict[str, Any]]:
    """Drop chunks below the relevance threshold."""

    filtered = [result for result in results if _safe_score(result) >= min_score]

    logger.debug(
        "Filtered chunks by score | min_score=%.3f | before=%d | after=%d",
        min_score,
        len(results),
        len(filtered),
    )

    return filtered


def filter_by_document(
    results: list[dict[str, Any]],
    document_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Keep only chunks from a specific document.

    If document_id is None, return the original list.
    """

    if document_id is None:
        return results

    filtered = [result for result in results if result.get("document_id") == document_id]

    logger.debug(
        "Filtered chunks by document | document_id=%s | before=%d | after=%d",
        document_id,
        len(results),
        len(filtered),
    )

    return filtered


def apply_filters(
    results: list[dict[str, Any]],
    *,
    min_score: float | None = None,
    document_id: str | None = None,
    dedup: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Apply retrieval post-processing.

    Steps:
    1. Deduplicate chunks
    2. Optionally filter by document
    3. Filter by relevance score
    4. Sort by score descending
    5. Optionally limit number of chunks
    """

    if not results:
        return []

    min_score = settings.min_retrieval_score if min_score is None else min_score

    logger.debug(
        "Starting retrieval filtering | chunks=%d | min_score=%.3f | document_id=%s",
        len(results),
        min_score,
        document_id,
    )

    if dedup:
        results = deduplicate(results)

    results = filter_by_document(results, document_id)
    results = filter_by_score(results, min_score)

    results = sorted(
        results,
        key=_safe_score,
        reverse=True,
    )

    if limit is not None:
        results = results[:limit]

    logger.debug("Final filtered chunks | count=%d", len(results))

    return results
