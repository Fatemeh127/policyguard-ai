"""
RAG pipeline — production-grade implementation with safety + tracing.
"""

from typing import Optional, Tuple, List
import time

from app.core.logging import get_logger
from app.observability.trace_logger import TraceLogger
from app.llm.safety import check_content_safety, filter_harmful_content
from app.retrieval.vector_store import VectorStore
from app.api.deps import get_vector_store
from app.retrieval.retriever import retrieve_chunks_with_metadata
from app.llm.answer_service import generate_answer
from app.schemas.ask import AskResponse
from app.core.request_context import get_request_id

logger = get_logger(__name__)

class RAGPipeline:

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or get_vector_store()

    # Prompt Injection Detection
    def _is_prompt_injection(self, query: str) -> bool:
        patterns = [
            "ignore previous instructions",
            "forget everything",
            "act as",
            "system prompt",
            "reveal system",
            "bypass",
        ]
        q = query.lower()
        return any(p in q for p in patterns)

    # Main pipeline
    def run(
        self,
        query: str,
        role: str,
        limit: int = 5
    ) -> Tuple[AskResponse, List[dict]]:

        trace = TraceLogger(component="RAGPipeline")

        start_time = time.time()

        try:
            # Layer 1: Input Safety
            with trace.span("input_safety"):

                safe_query = filter_harmful_content(query)

                if safe_query is None:
                    trace.log_blocked("content_filter")
                    return self._blocked_response(), []

                if not check_content_safety(safe_query):
                    trace.log_blocked("moderation")
                    return self._blocked_response(), []

                query = safe_query.strip()

            # Layer 2: Prompt Injection
            if self._is_prompt_injection(query):
                trace.log_blocked("prompt_injection")
                return self._blocked_response(), []

            # Layer 3: Retrieval
            with trace.span("retrieval"):

                chunks = retrieve_chunks_with_metadata(
                    query=query,
                    vector_store=self.vector_store,
                    role=role,
                    top_k=limit
                )

                if not chunks:
                    trace.log_fallback("no_chunks")
                    return self._fallback(), []

                max_score = max((c.get("score", 0) for c in chunks), default=0)
                trace.log_retrieval(len(chunks), max_score)

            # Generation
            with trace.span("generation"):

                try:
                    result = generate_answer(
                        query=query,
                        context_chunks=chunks   
                    )
                except Exception as e:
                    trace.error("generation_failed", error=str(e))
                    return self._fallback(), chunks

                if not result:
                    trace.log_fallback("empty_result")
                    return self._fallback(), chunks

            # Normalize Output
            answer = (result.get("answer") or "").strip()
            sources = result.get("sources", [])
            metadata = result.get("metadata", {})

            if not answer:
                trace.log_fallback("empty_answer")
                return self._fallback(), chunks

            trace.log_generation(len(answer))

            response = AskResponse(
                answer=answer,
                sources=sources,
                context_used=True,
                metadata={
                    **metadata,
                    "chunks_used": len(chunks),
                    "latency_seconds": round(time.time() - start_time, 3),
                    "max_retrieval_score": max_score,
                    "request_id": get_request_id(),
                }
            )

            return response, chunks

        except Exception as e:
            logger.exception("Pipeline failed completely")
            trace.error("pipeline_failed", error=str(e))
            return self._fallback(), []

    # Blocked Response
    def _blocked_response(self) -> AskResponse:
        return AskResponse(
            answer="Your request was blocked due to safety policies.",
            sources=[],
            context_used=False,
            metadata={"blocked": True}
        )

    # Fallback Response
    def _fallback(self) -> AskResponse:
        return AskResponse(
            answer="I couldn't find enough relevant information to answer. Please try rephrasing your question.",
            sources=[],
            context_used=False,
            metadata={}
        )