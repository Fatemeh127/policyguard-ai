"""Production-grade RAG pipeline with safety, tracing, RBAC, and observability."""

from __future__ import annotations

import re
import time
from typing import Any

from app.api.deps import get_vector_store
from app.core.config import settings
from app.core.logging import get_logger
from app.llm.answer_service import generate_answer
from app.llm.safety import moderate_content
from app.middleware.request_context import get_request_id
from app.observability.trace_logger import TraceLogger
from app.retrieval.retriever import retrieve_chunks_with_metadata
from app.retrieval.vector_store import VectorStore
from app.schemas.ask import AskResponse

logger = get_logger(__name__)


PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+previous\s+instructions",
    r"forget\s+everything",
    r"act\s+as\s+",
    r"system\s+prompt",
    r"reveal\s+system",
    r"bypass",
)

VALID_ROLES = {"employee", "manager", "admin"}


class RAGPipeline:
    """Main Retrieval-Augmented Generation orchestration pipeline."""

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self.vector_store = vector_store or get_vector_store()

    def _is_prompt_injection(self, query: str) -> bool:
        normalized_query = query.lower()
        return any(re.search(pattern, normalized_query) for pattern in PROMPT_INJECTION_PATTERNS)

    def _validate_inputs(self, query: str, role: str, limit: int) -> str | None:
        if role not in VALID_ROLES:
            return "Invalid role."

        if not query.strip():
            return "Query cannot be empty."

        if len(query) > 5000:
            return "Query is too large."

        if limit <= 0 or limit > 20:
            return "Invalid retrieval limit."

        return None

    def run(
        self,
        query: str,
        role: str,
        limit: int = 5,
    ) -> tuple[AskResponse, list[dict[str, Any]]]:
        trace = TraceLogger(component="RAGPipeline")
        start_time = time.perf_counter()

        validation_error = self._validate_inputs(query=query, role=role, limit=limit)

        if validation_error:
            trace.log_blocked("validation_failed")
            return self._error_response(validation_error), []

        try:
            with trace.span("input_safety"):
                moderation = moderate_content(query)

                if moderation.blocked:
                    trace.log_blocked(moderation.reason or "moderation_blocked")
                    return self._blocked_response(), []

                query = query.strip()

            if self._is_prompt_injection(query):
                trace.log_blocked("prompt_injection")
                logger.warning(
                    "Prompt injection attempt detected | request_id=%s",
                    get_request_id(),
                )
                return self._blocked_response(), []

            with trace.span("retrieval"):
                chunks = retrieve_chunks_with_metadata(
                    query=query,
                    vector_store=self.vector_store,
                    role=role,
                    top_k=limit,
                )

                if not chunks:
                    trace.log_fallback("no_chunks")
                    return self._fallback_response(), []

                max_score = max(
                    (float(chunk.get("score") or 0.0) for chunk in chunks),
                    default=0.0,
                )

                trace.log_retrieval(
                    chunk_count=len(chunks),
                    max_score=max_score,
                )

                if max_score < settings.min_retrieval_score:
                    trace.log_fallback("low_retrieval_score")
                    return self._fallback_response(), chunks

            with trace.span("generation"):
                try:
                    result = generate_answer(
                        query=query,
                        context_chunks=chunks,
                    )
                except Exception:
                    logger.exception("LLM generation failed")
                    trace.error("generation_failed")
                    return self._fallback_response(), chunks

                if not result:
                    trace.log_fallback("empty_generation_result")
                    return self._fallback_response(), chunks

            answer = str(result.get("answer", "")).strip()
            sources = result.get("sources", [])
            metadata = result.get("metadata", {})

            if not answer:
                trace.log_fallback("empty_answer")
                return self._fallback_response(), chunks

            latency_seconds = round(time.perf_counter() - start_time, 3)

            trace.log_generation(len(answer))

            response = AskResponse(
                answer=answer,
                sources=sources,
                context_used=True,
                metadata={
                    **metadata,
                    "chunks_used": len(chunks),
                    "latency_seconds": latency_seconds,
                    "max_retrieval_score": max_score,
                    "request_id": get_request_id(),
                },
            )

            logger.info(
                "Pipeline completed successfully | chunks=%d | latency=%.3fs | request_id=%s",
                len(chunks),
                latency_seconds,
                get_request_id(),
            )

            return response, chunks

        except Exception:
            logger.exception("Pipeline failed completely")
            trace.error("pipeline_failed")
            return self._fallback_response(), []

    def _blocked_response(self) -> AskResponse:
        return AskResponse(
            answer="Your request was blocked due to safety policies.",
            sources=[],
            context_used=False,
            metadata={"blocked": True},
        )

    def _fallback_response(self) -> AskResponse:
        return AskResponse(
            answer=(
                "I couldn't find enough relevant information to answer your request. "
                "Please try rephrasing your question."
            ),
            sources=[],
            context_used=False,
            metadata={},
        )

    def _error_response(self, message: str) -> AskResponse:
        return AskResponse(
            answer=message,
            sources=[],
            context_used=False,
            metadata={"error": True},
        )
