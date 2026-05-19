"""OpenAI embeddings service."""

import logging

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global client (reused across calls)
client = OpenAI(api_key=settings.openai_api_key)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


def get_embedding(text: str) -> list[float]:
    """
    Convert text to embedding vector using OpenAI.

    Args:
        text: Input text to embed

    Returns:
        List of floats (1536 dimensions for text-embedding-3-small)

    Raises:
        ValueError: If text is empty
        EmbeddingError: If OpenAI API fails
    """
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty")

    cleaned_text = text.strip()

    try:
        logger.debug("Generating embedding for text (length: %d chars)", len(cleaned_text))

        response = client.embeddings.create(input=cleaned_text, model="text-embedding-3-small")

        embedding = response.data[0].embedding

        logger.debug("Successfully generated %d-dimensional embedding", len(embedding))

        return embedding

    except Exception as exc:
        logger.exception("Failed to generate embedding")
        raise EmbeddingError("Embedding generation failed") from exc
