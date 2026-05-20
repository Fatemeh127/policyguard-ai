"""Metrics endpoint for usage tracking."""

import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.observability.usage_tracker import UsageTracker, get_usage_tracker
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/metrics")
async def get_metrics(tracker: UsageTracker = Depends(get_usage_tracker)) -> dict[str, Any]:
    """
    Get system usage metrics.

    Returns:
        - usage: request and token counts
        - cost: estimated OpenAI costs
        - performance: latency percentiles
        - vector_store: document counts
    """
    try:
        # Get usage metrics from Redis
        metrics = tracker.get_metrics()

        # Add vector store info
        try:
            vs = VectorStore()
            collection_info = vs.client.get_collection(vs.collection_name)

            metrics["vector_store"] = {
                "collection_name": vs.collection_name,
                "total_chunks": collection_info.points_count,
            }
        except Exception as e:
            logger.warning("Failed to get vector store metrics: %s", e)
            metrics["vector_store"] = {"error": "unavailable"}

        return metrics

    except Exception as e:
        logger.exception("Failed to retrieve metrics")
        return {"error": "Metrics retrieval failed", "detail": str(e)}
