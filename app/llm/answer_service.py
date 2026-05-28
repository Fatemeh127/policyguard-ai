"""LLM-based answer generation service."""

import logging
from typing import Any, Protocol

from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.llm.prompts import NO_CONTEXT_MESSAGE, SYSTEM_PROMPT_RAG, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Interface for LLM clients."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text from system and user prompts."""
        ...


class OpenAIClient:
    """OpenAI-backed LLM client."""

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate an answer using OpenAI chat completions."""

        response = self.client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens,
        )

        return response.choices[0].message.content or ""


class FakeLLMClient:
    """Fake LLM client for tests."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return a deterministic fake answer for tests."""

        return "This is a fake answer for testing."


def _filter_relevant_chunks(
    context_chunks: list[dict[str, Any]],
    min_score: float,
) -> list[dict[str, Any]]:
    """Keep only chunks that meet the minimum retrieval score."""

    return [chunk for chunk in context_chunks if float(chunk.get("score") or 0.0) >= min_score]


def _build_context_text(chunks: list[dict[str, Any]]) -> str:
    """Build LLM context text from retrieved chunks."""

    return "\n\n".join(
        f"[Source {index}]\n"
        f"Document: {chunk.get('document_id', 'unknown')}\n"
        f"Chunk ID: {chunk.get('chunk_id', 'unknown')}\n"
        f"Content:\n{chunk.get('text', '')}"
        for index, chunk in enumerate(chunks, start=1)
    )


def _build_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build source metadata for the API response."""

    return [
        {
            "document_id": chunk.get("document_id"),
            "chunk_id": chunk.get("chunk_id"),
            "score": chunk.get("score"),
        }
        for chunk in chunks
    ]


def generate_answer(
    query: str,
    context_chunks: list[dict[str, Any]],
    min_score: float | None = None,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Generate an answer from retrieved RAG context."""

    min_score = min_score if min_score is not None else settings.min_retrieval_score
    llm = llm or OpenAIClient()

    relevant_chunks = _filter_relevant_chunks(
        context_chunks=context_chunks,
        min_score=min_score,
    )

    if not relevant_chunks:
        logger.info("No relevant chunks found for query | min_score=%s", min_score)

        return {
            "answer": NO_CONTEXT_MESSAGE,
            "sources": [],
            "context_used": False,
            "metadata": {
                "num_chunks_used": 0,
                "min_score_threshold": min_score,
                "model": settings.openai_chat_model,
            },
        }

    context_text = _build_context_text(relevant_chunks)

    try:
        logger.debug("Generating answer with %d chunks", len(relevant_chunks))

        content = llm.generate(
            system_prompt=SYSTEM_PROMPT_RAG,
            user_prompt=USER_PROMPT_TEMPLATE.format(
                context=context_text,
                query=query,
            ),
        )

        answer = content.strip()

        if not answer:
            logger.warning("LLM returned an empty answer")

            return {
                "answer": NO_CONTEXT_MESSAGE,
                "sources": _build_sources(relevant_chunks),
                "context_used": False,
                "metadata": {
                    "num_chunks_used": len(relevant_chunks),
                    "model": settings.openai_chat_model,
                    "min_score_threshold": min_score,
                    "empty_answer": True,
                },
            }

        return {
            "answer": answer,
            "sources": _build_sources(relevant_chunks),
            "context_used": True,
            "metadata": {
                "num_chunks_used": len(relevant_chunks),
                "model": settings.openai_chat_model,
                "min_score_threshold": min_score,
            },
        }

    except OpenAIError as exc:
        logger.exception("OpenAI generation failed")
        raise RuntimeError("OpenAI answer generation failed") from exc

    except Exception as exc:
        logger.exception("Unexpected LLM generation failure")
        raise RuntimeError("Answer generation failed") from exc
