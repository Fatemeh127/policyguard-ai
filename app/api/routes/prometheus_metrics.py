"""Prometheus-compatible metrics endpoint."""

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from starlette.responses import Response

from app.observability.usage_tracker import get_usage_tracker
from app.retrieval.vector_store import VectorStore

router = APIRouter()

TOTAL_REQUESTS = Gauge(
    "policyguard_total_requests",
    "Total requests tracked by PolicyGuard AI",
)

TOTAL_TOKENS = Gauge(
    "policyguard_total_tokens",
    "Total tokens used by PolicyGuard AI",
)

TOTAL_COST = Gauge(
    "policyguard_total_cost",
    "Estimated total OpenAI cost",
)

AVG_LATENCY_MS = Gauge(
    "policyguard_avg_latency_ms",
    "Average request latency in milliseconds",
)

VECTOR_STORE_CHUNKS = Gauge(
    "policyguard_vector_store_chunks",
    "Total chunks stored in the vector database",
)


@router.get("/metrics")
def prometheus_metrics() -> Response:
    """Expose metrics in Prometheus text format."""
    tracker = get_usage_tracker()
    metrics = tracker.get_metrics()

    usage = metrics.get("usage", {})
    cost = metrics.get("cost", {})
    performance = metrics.get("performance", {})

    TOTAL_REQUESTS.set(float(usage.get("total_requests", 0)))
    TOTAL_TOKENS.set(float(usage.get("total_tokens", 0)))
    TOTAL_COST.set(float(cost.get("total_cost", 0)))
    AVG_LATENCY_MS.set(float(performance.get("avg_latency_ms", 0)))

    try:
        vs = VectorStore()
        collection_info = vs.client.get_collection(vs.collection_name)

        points_count = collection_info.points_count or 0
        VECTOR_STORE_CHUNKS.set(float(points_count))

    except Exception:
        VECTOR_STORE_CHUNKS.set(0)

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
