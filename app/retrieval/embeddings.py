"""OpenAI embeddings service."""

import logging

from openai import OpenAI, OpenAIError

from app.core.config import settings
from app.observability.prometheus_metrics import openai_cost_total, openai_tokens_total

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.openai_api_key)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


def calculate_embedding_cost(tokens: int) -> float:
    """Calculate embedding cost in USD."""

    return (tokens / 1_000_000) * settings.cost_embedding_per_m


def get_embedding(text: str) -> list[float]:
    """Convert text to an embedding vector using the configured embedding model."""

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

        if response.usage is not None:
            embedding_tokens = response.usage.total_tokens

            openai_tokens_total.labels(type="embedding").inc(embedding_tokens)

            request_cost = calculate_embedding_cost(tokens=embedding_tokens)
            openai_cost_total.inc(request_cost)

        embedding = response.data[0].embedding

        logger.debug(
            "Embedding generated successfully | dimensions=%d",
            len(embedding),
        )

        return embedding

    except OpenAIError as exc:
        logger.exception("OpenAI embedding request failed")
        raise EmbeddingError("Embedding generation failed") from exc
