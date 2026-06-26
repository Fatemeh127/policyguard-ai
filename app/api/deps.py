"""Provide a shared singleton instance of the vector store."""

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.core.redis import get_redis_client
from app.observability.usage_tracker import (
    UsageTracker,
    get_usage_tracker,
)
from app.retrieval.vector_store import VectorStore
from app.services.ask_service import AskService

_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """
    Return a cached singleton instance of the vector store.
    """

    global _vector_store

    if _vector_store is None:
        _vector_store = VectorStore()

    return _vector_store

def get_ask_service(
    vs: Annotated[VectorStore, Depends(get_vector_store)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    tracker: Annotated[UsageTracker, Depends(get_usage_tracker)],
) -> AskService:
    return AskService(
        vector_store=vs,
        redis=redis,
        tracker=tracker,
    )