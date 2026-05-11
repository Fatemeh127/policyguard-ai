"""Health check endpoint."""
import logging
import time
from fastapi import APIRouter
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.retrieval.vector_store import VectorStore

from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

START_TIME = time.time()

# Reuse single instance (important for performance)
vector_store = VectorStore()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    System health check endpoint.
    Checks core dependencies without heavy computation.
    """

    qdrant_status = "unhealthy"
    points_count = 0

    # Qdrant health check
    try:
        collection = vector_store.client.get_collection(
            collection_name=vector_store.collection_name
        )

        points_count = collection.points_count
        qdrant_status = "healthy"

    except UnexpectedResponse as e:
        logger.error("Qdrant responded with error: %s", e)

    except Exception as e:
        logger.exception("Qdrant health check failed")

    # OpenAI config check
    openai_status = (
        "configured"
        if getattr(settings, "openai_api_key", None)
        else "missing"
    )

    # Overall system status
    overall_status : str = "healthy"
    if qdrant_status != "healthy":
        overall_status = "degraded"
    if openai_status != "configured":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "components": {
            "qdrant": {
                "status": qdrant_status,
                "collection": vector_store.collection_name,
                "points_count": points_count,
            },
            "openai": {
                "status": openai_status,
            },
        },
        "environment": settings.environment,
        "metadata": {
            "uptime_seconds": int(time.time() - START_TIME)
        }
    }