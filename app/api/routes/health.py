"""Health check endpoint."""

import logging
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from qdrant_client.http.exceptions import UnexpectedResponse

from app.api.deps import get_vector_store
from app.core.config import settings
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)
router = APIRouter()

START_TIME = time.time()


@router.get("/health")
async def health_check(
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> dict[str, Any]:
    """
    System health check endpoint.
    Checks core dependencies without heavy computation.
    """

    qdrant_status = "unhealthy"
    points_count = 0

    try:
        collection_info = vector_store.client.get_collection(
            collection_name=vector_store.collection_name
        )

        points_count = collection_info.points_count or 0
        qdrant_status = "healthy"

    except UnexpectedResponse as e:
        logger.error("Qdrant responded with error: %s", e)

    except Exception:
        logger.exception("Qdrant health check failed")

    openai_status = "configured" if getattr(settings, "openai_api_key", None) else "missing"

    overall_status: str = "healthy"
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
        "metadata": {"uptime_seconds": int(time.time() - START_TIME)},
    }