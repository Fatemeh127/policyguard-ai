"""
Ask endpoint — production-grade RAG Q&A API.
"""

import asyncio
import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis.asyncio import Redis

from app.api.deps import get_vector_store
from app.core.dependencies import get_current_role
from app.ingestion.pipeline import RAGPipeline
from app.middleware.rate_limiter import limiter
from app.observability.usage_tracker import UsageTracker, get_usage_tracker
from app.retrieval.vector_store import VectorStore
from app.schemas.ask import AskRequest, AskResponse
from app.services.chat_memory import get_chat_history, save_chat_history

logger = logging.getLogger(__name__)
router = APIRouter()


redis_client = Redis(host="redis", port=6379, decode_responses=True)


def get_redis() -> Redis:
    return redis_client


@router.post("/ask", response_model=AskResponse)
@limiter.limit("10/minute")
async def ask_question(
    request: Request,
    response: Response,
    ask_request: AskRequest,
    vs: Annotated[VectorStore, Depends(get_vector_store)],
    tracker: Annotated[UsageTracker, Depends(get_usage_tracker)],
    user_role: Annotated[str, Depends(get_current_role)],
    redis: Redis = Depends(get_redis),
) -> AskResponse:
    start_time = time.time()

    try:
        logger.info(
            "Question received | authenticated_role=%s | claimed_role=%s | query_length=%d",
            user_role,
            ask_request.role,
            len(ask_request.query),
        )

        # --- Load chat history ---
        history = await get_chat_history(ask_request.session_id, redis)

        history.append({"role": "user", "content": ask_request.query})

        # --- Build RAG query (conversation-aware) ---
        context_query = "\n".join([m["content"] for m in history[-6:]])

        pipeline = RAGPipeline(vector_store=vs)

        rag_response, chunks = await asyncio.to_thread(
            pipeline.run, query=context_query, role=user_role, limit=ask_request.limit
        )

        # --- Save assistant response ---
        history.append({"role": "assistant", "content": rag_response.answer})

        await save_chat_history(ask_request.session_id, history, redis)

        # --- Metrics ---
        latency_sec = time.time() - start_time
        latency_ms = latency_sec * 1000

        query_tokens = max(len(ask_request.query) // 4, 1)

        context_text = "\n\n".join([c.get("text", "") for c in chunks if isinstance(c, dict)])

        context_tokens = len(context_text) // 4
        prompt_tokens = query_tokens + context_tokens + 100
        completion_tokens = len(rag_response.answer) // 4

        try:
            tracker.track_request(
                endpoint="ask",
                embedding_tokens=query_tokens,
                llm_prompt_tokens=prompt_tokens,
                llm_completion_tokens=completion_tokens,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.warning("Usage tracking failed: %s", str(e))

        # --- Headers ---
        response.headers["X-RateLimit-Limit"] = "10"
        response.headers["X-RateLimit-Remaining"] = "unknown"

        logger.info(
            "Ask completed | latency=%.3fs | chunks=%d | context_used=%s",
            latency_sec,
            len(chunks),
            rag_response.context_used,
        )

        return rag_response

    except Exception as exc:
        logger.exception("Ask endpoint failed")

        try:
            tracker.track_request(endpoint="ask", latency_ms=(time.time() - start_time) * 1000)
        except Exception as e:
            logger.warning("Failed to track request: %s", e)

        raise HTTPException(status_code=500, detail="Failed to process question") from exc
