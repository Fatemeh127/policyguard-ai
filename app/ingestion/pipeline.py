"""Production-grade RAG pipeline with safety, tracing, RBAC, and observability."""

from __future__ import annotations

import time
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.middleware.request_context import get_request_id
from app.observability.trace_logger import TraceLogger
from app.retrieval.retriever import RetrievalService
from app.schemas.ask import AskResponse
from app.services.rag.answer_generation_service import AnswerGenerationService
from app.services.rag.input_validation_service import InputValidationService
from app.services.rag.moderation_service import ModerationService
from app.services.rag.prompt_injection_service import PromptInjectionService
from app.services.rag.response_builder import (
    blocked_response,
    error_response,
    fallback_response,
)

logger = get_logger(__name__)


class RAGPipeline:
    """Main Retrieval-Augmented Generation orchestration pipeline."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        moderation_service: ModerationService,
        prompt_injection_service: PromptInjectionService,
        validation_service: InputValidationService,
        answer_generation_service: AnswerGenerationService,
    ):
        self.retrieval_service = retrieval_service
        self.moderation_service = moderation_service
        self.prompt_injection_service = prompt_injection_service
        self.validation_service = validation_service
        self.answer_generation_service = answer_generation_service

    def run(
        self,
        query: str,
        role: str,
        limit: int = 5,
    ) -> tuple[AskResponse, list[dict[str, Any]]]:
        trace = TraceLogger(component="RAGPipeline")

        start_time = time.perf_counter()

        validation_error = self.validation_service.validate(
            query=query,
            role=role,
            limit=limit,
        )

        if validation_error:
            trace.log_blocked("validation_failed")

            return error_response(validation_error), []

        try:
            # Safety
            with trace.span("input_safety"):
                moderation = self.moderation_service.check(query)

                if moderation.blocked:
                    trace.log_blocked(moderation.reason or "moderation_blocked")

                    return blocked_response(), []

                query = query.strip()

            # Prompt Injection
            if self.prompt_injection_service.detect(query):
                trace.log_blocked("prompt_injection")

                logger.warning(
                    "Prompt injection attempt detected | request_id=%s",
                    get_request_id(),
                )

                return blocked_response(), []

            # Retrieval
            with trace.span("retrieval"):
                chunks = self.retrieval_service.retrieve_chunks_with_metadata(
                    query=query,
                    role=role,
                    top_k=limit,
                )

                if not chunks:
                    trace.log_fallback("no_chunks")

                    return fallback_response(), []

                max_score = max(
                    (float(chunk.get("score") or 0.0) for chunk in chunks),
                    default=0.0,
                )

                try:
                    trace.log_retrieval(
                        num_chunks=len(chunks),
                        max_score=max_score,
                    )

                except Exception:
                    logger.exception("Retrieval tracing failed")

                if max_score < settings.min_retrieval_score:
                    trace.log_fallback("low_retrieval_score")

                    logger.warning(
                        "Retrieval score below threshold | max_score=%.3f | threshold=%.3f",
                        max_score,
                        settings.min_retrieval_score,
                    )

                    return fallback_response(), chunks

            # Generation
            with trace.span("generation"):
                result = self.answer_generation_service.generate(
                    query=query,
                    chunks=chunks,
                )

                if result is None:
                    trace.error("generation_failed")
                    return fallback_response(), chunks
                if not result:
                    trace.log_fallback("empty_generation_result")

                    return fallback_response(), chunks

            answer = str(result.get("answer", "")).strip()

            sources = result.get("sources", [])

            metadata = result.get("metadata", {})

            if not answer:
                trace.log_fallback("empty_answer")

                return fallback_response(), chunks

            latency_seconds = round(
                time.perf_counter() - start_time,
                3,
            )

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

            return fallback_response(), []
