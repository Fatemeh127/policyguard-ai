"""Prometheus metrics for PolicyGuard AI."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

RAG_REQUESTS_TOTAL = Counter(
    "policyguard_rag_requests_total",
    "Total RAG requests",
)

RAG_TOKENS_TOTAL = Counter(
    "policyguard_rag_tokens_total",
    "Total tokens used by RAG",
    ["type"],
)

RAG_COST_TOTAL = Gauge(
    "policyguard_rag_cost_total",
    "Total estimated RAG cost",
)

RAG_LATENCY_MS = Histogram(
    "policyguard_rag_latency_ms",
    "RAG request latency in milliseconds",
)

VECTOR_STORE_CHUNKS = Gauge(
    "policyguard_vector_store_chunks",
    "Total chunks stored in vector database",
)


def metrics_response() -> Response:
    """Return Prometheus-formatted metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
