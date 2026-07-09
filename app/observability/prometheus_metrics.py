"""Prometheus metrics exporter for FastAPI."""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Metrics definitions
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

openai_tokens_total = Counter(
    "openai_tokens_total",
    "Total OpenAI tokens used",
    ["type"],  # embedding, prompt, completion
)

openai_cost_total = Counter(
    "openai_cost_total",
    "Total OpenAI cost in USD",
)

qdrant_documents_total = Gauge(
    "qdrant_documents_total",
    "Total documents in Qdrant",
)


# Middleware
class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:

        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        return response


# Metrics endpoint
async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
