"""Answer generation service for RAG."""

from typing import Any

from app.core.logging import get_logger
from app.llm.answer_service import generate_answer

logger = get_logger(__name__)


def generate_rag_answer(
    query: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Generate an answer using the retrieved context chunks."""

    try:
        return generate_answer(
            query=query,
            context_chunks=chunks,
        )
    except Exception:
        logger.exception("LLM generation failed")
        return None
