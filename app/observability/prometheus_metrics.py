"""Prometheus metrics exporter for FastAPI."""

import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Define metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)

openai_tokens_total = Counter(
    "openai_tokens_total", "Total OpenAI tokens used", ["type"]  # embedding, prompt, completion
)

openai_cost_total = Gauge("openai_cost_total", "Total OpenAI cost in USD")

qdrant_documents_total = Gauge("qdrant_documents_total", "Total documents in Qdrant")


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP metrics."""

    async def dispatch(self, request: Request, call_next):
        """Track request metrics."""
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method, endpoint=request.url.path, status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method, endpoint=request.url.path
        ).observe(duration)

        return response


async def metrics_endpoint():
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
