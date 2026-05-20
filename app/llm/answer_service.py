"""LLM-based answer generation service."""

import logging
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.llm.prompts import NO_CONTEXT_MESSAGE, SYSTEM_PROMPT_RAG, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)

class LLMClient:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError
    
class OpenAIClient(LLMClient):
    def __init__(self, client):
        self.client = client

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=500,
        )
        return response.choices[0].message.content


def generate_answer(
    query: str,
    context_chunks: list[dict[str, Any]],
    min_score: float = 0.5,
    llm: LLMClient = None,
) -> dict[str, Any]:

    if llm is None:
        llm = OpenAIClient(client)

    # fallback if no context or low relevance
    if not context_chunks or all(chunk.get("score", 0) < min_score for chunk in context_chunks):
        return {
            "answer": "I don't have enough information to answer that based on the available documents.",
            "sources": [],
            "context_used": False,
            "metadata": {"num_chunks_used": 0, "model": "gpt-3.5-turbo"},
        }

    relevant_chunks = context_chunks

    if not relevant_chunks:
        logger.warning("No relevant chunks found for query (min_score=%f)", min_score)
        return {
            "answer": NO_CONTEXT_MESSAGE,
            "sources": [],
            "context_used": False,
            "metadata": {"num_chunks_used": 0, "min_score_threshold": min_score},
        }

    context_text = "\n\n".join(
        f"[Source {i+1}] {chunk['text']}" for i, chunk in enumerate(relevant_chunks)
    )

    try:
        logger.debug("Generating answer with %d chunks", len(relevant_chunks))

        content = llm.generate(
            SYSTEM_PROMPT_RAG,
            USER_PROMPT_TEMPLATE.format(context=context_text, query=query),
        )

        answer = (content or "").strip()

        return {
            "answer": answer,
            "sources": [
                {
                    "document_id": chunk.get("document_id"),
                    "chunk_id": chunk.get("chunk_id"),
                    "score": chunk.get("score"),
                }
                for chunk in relevant_chunks
            ],
            "context_used": True,
            "metadata": {
                "num_chunks_used": len(relevant_chunks),
                "model": "gpt-3.5-turbo",
            },
        }

    except Exception as exc:
        logger.exception("LLM generation failed")
        raise RuntimeError("Answer generation failed") from exc