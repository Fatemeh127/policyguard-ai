"""Service layer for handling Ask/RAG question flow."""

import asyncio
import logging
import time

from redis.asyncio import Redis

from app.ingestion.pipeline import RAGPipeline
from app.observability.usage_tracker import UsageTracker
from app.schemas.ask import AskRequest, AskResponse
from app.schemas.common import Source
from app.services.chat_memory import get_chat_history, save_chat_history
from app.services.response_cache import (
    get_cached_response,
    make_cache_key,
    save_cached_response,
)

logger = logging.getLogger(__name__)


class AskService:
    """Coordinates the RAG question-answering flow."""

    def __init__(
        self,
        pipeline: RAGPipeline,
        redis: Redis,
        tracker: UsageTracker,
    ) -> None:
        self.pipeline = pipeline
        self.redis = redis
        self.tracker = tracker

    async def answer_question(
        self,
        ask_request: AskRequest,
        user_role: str,
    ) -> AskResponse:
        start_time = time.time()

        history = await get_chat_history(ask_request.session_id, self.redis)
        history.append({"role": "user", "content": ask_request.query})

        cache_key = make_cache_key(
            query=ask_request.query,
            role=user_role,
            limit=ask_request.limit,
        )

        cached_response = await get_cached_response(self.redis, cache_key)

        if cached_response is not None:
            logger.info("Cache hit for ask service")

            cached_ask_response = AskResponse(**cached_response)

            history.append({"role": "assistant", "content": cached_ask_response.answer})
            await save_chat_history(ask_request.session_id, history, self.redis)

            if cached_ask_response.metadata is None:
                cached_ask_response.metadata = {}

            latency_sec = time.time() - start_time

            cached_ask_response.metadata.update(
                {
                    "cache": "HIT",
                    "latency_seconds": latency_sec,
                }
            )

            return cached_ask_response

        logger.info("Cache miss for ask service")

        rag_response, chunks = await asyncio.to_thread(
            self.pipeline.run,
            query=ask_request.query,
            role=user_role,
            limit=ask_request.limit,
        )

        history.append({"role": "assistant", "content": rag_response.answer})
        await save_chat_history(ask_request.session_id, history, self.redis)

        latency_sec = time.time() - start_time
        latency_ms = latency_sec * 1000

        query_tokens = max(len(ask_request.query) // 4, 1)

        context_text = "\n\n".join([c.get("text", "") for c in chunks if isinstance(c, dict)])

        context_tokens = len(context_text) // 4
        prompt_tokens = query_tokens + context_tokens + 100
        completion_tokens = len(rag_response.answer) // 4
        total_tokens = prompt_tokens + completion_tokens

        scores: list[float] = [
            float(c["score"])
            for c in chunks
            if isinstance(c, dict) and isinstance(c.get("score"), (int, float))
        ]

        confidence = round(sum(scores) / len(scores), 3) if scores else 0.0

        try:
            self.tracker.track_request(
                endpoint="ask",
                embedding_tokens=query_tokens,
                llm_prompt_tokens=prompt_tokens,
                llm_completion_tokens=completion_tokens,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.warning("Usage tracking failed: %s", str(e))

        if rag_response.metadata is None:
            rag_response.metadata = {}

        rag_response.metadata.update(
            {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "latency_seconds": latency_sec,
                "confidence": confidence,
                "cache": "MISS",
            }
        )

        rag_response.sources = [
            Source(
                document_id=str(c.get("document_id", "Unknown")),
                chunk_id=int(c.get("chunk_id", 0)),
                score=float(c.get("score", 0.0)),
                text=str(c.get("text", "")),
            )
            for c in chunks
            if isinstance(c, dict)
        ]

        await save_cached_response(
            redis=self.redis,
            cache_key=cache_key,
            response_data=rag_response.model_dump(),
        )

        return rag_response
