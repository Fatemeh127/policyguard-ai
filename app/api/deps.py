"""Provide shared dependency instances."""

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.core.redis import get_redis_client
from app.ingestion.pipeline import RAGPipeline
from app.observability.usage_tracker import UsageTracker, get_usage_tracker
from app.retrieval.retriever import RetrievalService
from app.retrieval.vector_store import VectorStore
from app.services.ask_service import AskService
from app.services.rag.answer_generation_service import AnswerGenerationService
from app.services.rag.input_validation_service import InputValidationService
from app.services.rag.moderation_service import ModerationService
from app.services.rag.prompt_injection_service import PromptInjectionService

_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Return a cached singleton instance of the vector store."""

    global _vector_store

    if _vector_store is None:
        _vector_store = VectorStore()

    return _vector_store


def get_retrieval_service(
    vs: Annotated[VectorStore, Depends(get_vector_store)],
) -> RetrievalService:
    return RetrievalService(vector_store=vs)


def get_moderation_service() -> ModerationService:
    return ModerationService()


def get_input_validation_service() -> InputValidationService:
    return InputValidationService()


def get_prompt_injection_service() -> PromptInjectionService:
    return PromptInjectionService()


def get_answer_generation_service() -> AnswerGenerationService:
    return AnswerGenerationService()


def get_rag_pipeline(
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
    moderation_service: Annotated[ModerationService, Depends(get_moderation_service)],
    prompt_injection_service: Annotated[
        PromptInjectionService, Depends(get_prompt_injection_service)
    ],
    validation_service: Annotated[InputValidationService, Depends(get_input_validation_service)],
    answer_generation_service: Annotated[
        AnswerGenerationService, Depends(get_answer_generation_service)
    ],
) -> RAGPipeline:
    return RAGPipeline(
        retrieval_service=retrieval_service,
        moderation_service=moderation_service,
        prompt_injection_service=prompt_injection_service,
        validation_service=validation_service,
        answer_generation_service=answer_generation_service,
    )


def get_ask_service(
    pipeline: Annotated[RAGPipeline, Depends(get_rag_pipeline)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    tracker: Annotated[UsageTracker, Depends(get_usage_tracker)],
) -> AskService:
    return AskService(
        pipeline=pipeline,
        redis=redis,
        tracker=tracker,
    )
