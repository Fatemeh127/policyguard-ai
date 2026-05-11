"""FastAPI application initialization."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging

from app.api.routes import ask, eval
from app.observability.prometheus_metrics import PrometheusMiddleware, metrics_endpoint

from app.middleware.request_id import RequestIDMiddleware

from app.api.deps import get_vector_store
from app.ingestion.loaders.pdf_loader import load_pdf
from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text

logger = logging.getLogger(__name__)

setup_logging()

DEFAULT_PDF = "data/sample_docs/employee_handbook.pdf"


# Lifespan handler (replaces startup/shutdown events)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle events."""

    logger.info("Starting PolicyGuard AI API")
    logger.info("Environment: %s", settings.environment)

    vs = get_vector_store()

    try:
        logger.info("Loading default document...")

        text = load_pdf(DEFAULT_PDF)

        chunks = recursive_chunk_text(
            text,
            chunk_size=1000,
            chunk_overlap=200
        )

        vs.add_documents(
            chunks=chunks,
            document_id="default_handbook",
            role="employee"
        )

        logger.info("Default document loaded successfully (%d chunks)", len(chunks))

    except Exception as e:
        logger.error("Failed to load default document: %s", str(e))

    yield

    logger.info("Shutting down PolicyGuard AI API")


# Create FastAPI app
app = FastAPI(
    title="PolicyGuard AI",
    description="RAG-based organizational document assistant with RBAC",
    version="0.1.0",
    lifespan=lifespan
)

# Add request ID middleware
app.add_middleware(RequestIDMiddleware)


# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://172.20.10.6:8501", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PolicyGuard AI API",
        "version": "0.1.0",
        "status": "running"
    }

# Import and include routers
from app.api.routes import health, ask, ingest, metrics as metrics_route

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(ask.router, prefix="/api", tags=["Q&A"])
app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])
app.include_router(metrics_route.router, prefix="/api", tags=["Metrics"])
app.include_router(eval.router, prefix="/api/v1", tags=["eval"])