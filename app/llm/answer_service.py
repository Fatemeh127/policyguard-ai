"""LLM-based answer generation service."""
from app.llm.prompts import (
    SYSTEM_PROMPT_RAG,
    USER_PROMPT_TEMPLATE,
    NO_CONTEXT_MESSAGE
)
import logging
from typing import List, Dict, Any
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)

def generate_answer(
    query: str,
    context_chunks: List[Dict[str, Any]],
    min_score: float = 0.5
) -> Dict[str, Any]:
    """
    Generate answer using LLM with retrieved context.
    
    Args:
        query: User's question
        context_chunks: Retrieved chunks from vector store
        min_score: Minimum similarity score to use a chunk
        
    Returns:
        Dict with answer, sources, and metadata
    """
    # Filter by relevance score
    relevant_chunks = context_chunks

    # Safe fallback if no relevant context
    if not relevant_chunks:
        logger.warning(
            "No relevant chunks found for query (min_score=%f)",
            min_score
        )
        return {
            "answer": NO_CONTEXT_MESSAGE,
            "context_used": False,
            "metadata": {
                "num_chunks_used": 0,
                "min_score_threshold": min_score
            }
        }

    # Build context from chunks
    context_text = "\n\n".join(
        f"[Source {i+1}] {chunk['text']}"
        for i, chunk in enumerate(relevant_chunks)
    )

    try:
        logger.debug(
            "Generating answer with %d chunks",
            len(relevant_chunks)
        )
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RAG},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        context=context_text,
                        query=query
                    )   
                }
            ],
            temperature=0,
            max_tokens=500
        )

        answer = response.choices[0].message.content.strip()

        logger.info("Successfully generated answer")

        return {
            "answer": answer,
            "sources": [
                {
                    "document_id": chunk.get("document_id"),
                    "chunk_id": chunk.get("chunk_id"),
                    "score": chunk.get("score")
                }
                for chunk in relevant_chunks
            ],
            "context_used": True,
            "metadata": {
                "num_chunks_used": len(relevant_chunks),
                "model": "gpt-3.5-turbo",
                "min_score_threshold": min_score
            }
        }

    except Exception as exc:
        logger.exception("LLM generation failed")
        raise RuntimeError("Answer generation failed") from exc