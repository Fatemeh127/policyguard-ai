"""Answer generation service for RAG responses."""

from typing import Any

from app.services.rag.answer_generator import generate_rag_answer


class AnswerGenerationService:
    """Handles answer generation from retrieved chunks."""

    def generate(
        self,
        query: str,
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return generate_rag_answer(
            query=query,
            chunks=chunks,
        )
