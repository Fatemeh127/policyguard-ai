"""FastAPI application initialization for PolicyGuard AI."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ask, eval, health, ingest
from app.api.routes import metrics as metrics_route
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.startup import ensure_sample_data
from app.middleware.request_id import RequestIDMiddleware
from app.observability.prometheus_metrics import PrometheusMiddleware, metrics_endpoint

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage FastAPI application lifecycle events.
    """

    logger.info("Starting PolicyGuard AI API")
    logger.info("Environment: %s", settings.environment)

    ensure_sample_data(force_reload=False)

    yield

    logger.info("Shutting down PolicyGuard AI API")


app = FastAPI(
    title="PolicyGuard AI",
    description="RAG-based organizational document assistant with RBAC",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(PrometheusMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://172.20.10.6:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/metrics")
async def metrics() -> Any:
    """Prometheus metrics endpoint."""

    return await metrics_endpoint()


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint."""

    return {
        "message": "PolicyGuard AI API",
        "version": "0.1.0",
        "status": "running",
    }


app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(ask.router, prefix="/api", tags=["Q&A"])
app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])
app.include_router(metrics_route.router, prefix="/api", tags=["Metrics"])
app.include_router(eval.router, prefix="/api/v1", tags=["Evaluation"])
