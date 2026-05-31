"""OpenAI embeddings service."""

import logging

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


def get_embedding(text: str) -> list[float]:
    """
    Convert text to embedding vector using the configured embedding model.
    """

    if not text or not text.strip():
        raise ValueError("Input text cannot be empty")

    cleaned_text = text.strip()

    try:
        logger.debug(
            "Generating embedding | model=%s | text_length=%d",
            settings.embedding_model,
            len(cleaned_text),
        )

        response = client.embeddings.create(
            input=cleaned_text,
            model=settings.embedding_model,
        )

        embedding = response.data[0].embedding

        logger.debug(
            "Embedding generated successfully | dimensions=%d",
            len(embedding),
        )

        return embedding

    except Exception as exc:
        logger.exception("Failed to generate embedding")
        raise EmbeddingError("Embedding generation failed") from exc
